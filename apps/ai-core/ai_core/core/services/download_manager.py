import asyncio
import aiohttp
import aiofiles
import uuid
from pathlib import Path
from typing import Dict, Optional, AsyncGenerator
from fastapi import BackgroundTasks
from datetime import datetime
import logging
from ai_core.core.models import DownloadStatus, DownloadState

logger = logging.getLogger(__name__)


class DownloadManager:
    """Service for managing asynchronous model downloads"""

    def __init__(
        self, download_dir: Optional[str] = None, max_concurrent: Optional[int] = None
    ):
        """Initialize download manager

        Args:
            download_dir: Directory to store downloaded files
            max_concurrent: Maximum concurrent downloads
        """
        from ai_core.core.config.settings import config

        # Use config values if not provided
        if download_dir is None:
            download_dir = config.downloads_dir
        if max_concurrent is None:
            max_concurrent = config.max_concurrent_downloads

        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True, parents=True)
        self.max_concurrent = max_concurrent

        # Active downloads tracking
        self.active_downloads: Dict[str, DownloadStatus] = {}
        self.download_tasks: Dict[str, asyncio.Task] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent)

        # SSE subscribers
        self.subscribers: Dict[str, asyncio.Queue] = {}

    async def start_download(
        self, repo_id: str, filename: str, background_tasks: BackgroundTasks
    ) -> str:
        """Start downloading a model file

        Args:
            repo_id: Hugging Face repository ID
            filename: File to download

        Returns:
            Download ID for tracking
        """
        download_id = str(uuid.uuid4())

        # Check if already downloading
        existing_id = self._find_existing_download(repo_id, filename)
        if existing_id:
            logger.info(f"Download already in progress: {existing_id}")
            return existing_id

        # Create initial status
        status = DownloadStatus(
            download_id=download_id,
            repo_id=repo_id,
            filename=filename,
            status=DownloadState.PENDING,
            progress_percent=0.0,
            bytes_downloaded=0,
            total_bytes=None,
            download_speed_mbps=None,
            eta_seconds=None,
            error_message=None,
            started_at=datetime.utcnow(),
            completed_at=None,
        )

        self.active_downloads[download_id] = status

        # Start download task
        task = asyncio.create_task(self._download_file_task(download_id))
        self.download_tasks[download_id] = task

        # Notify subscribers
        await self._notify_subscribers(status)

        logger.info(f"Started download {download_id} for {repo_id}/{filename}")
        return download_id

    async def cancel_download(self, download_id: str) -> bool:
        """Cancel an active download

        Args:
            download_id: Download to cancel

        Returns:
            True if cancelled successfully
        """
        if download_id not in self.active_downloads:
            return False

        # Cancel the task
        if download_id in self.download_tasks:
            self.download_tasks[download_id].cancel()

        # Update status
        status = self.active_downloads[download_id]
        status.status = DownloadState.CANCELLED
        status.completed_at = datetime.utcnow()

        await self._notify_subscribers(status)

        logger.info(f"Cancelled download {download_id}")
        return True

    async def get_download_status(self, download_id: str) -> Optional[DownloadStatus]:
        """Get current status of a download

        Args:
            download_id: Download ID

        Returns:
            DownloadStatus or None if not found
        """
        return self.active_downloads.get(download_id)

    async def get_all_downloads(self) -> Dict[str, DownloadStatus]:
        """Get status of all active downloads"""
        return self.active_downloads.copy()

    async def subscribe_to_updates(
        self, subscriber_id: str
    ) -> AsyncGenerator[str, None]:
        """Subscribe to download status updates via SSE

        Args:
            subscriber_id: Unique subscriber identifier

        Yields:
            JSON-encoded DownloadStatus updates
        """
        # Create queue for this subscriber
        queue: asyncio.Queue[DownloadStatus] = asyncio.Queue()
        self.subscribers[subscriber_id] = queue

        try:
            # Send current status of all active downloads
            for status in self.active_downloads.values():
                await queue.put(status)

            # Stream updates
            while True:
                status = await queue.get()
                yield f"data: {status.json()}\n\n"

        except asyncio.CancelledError:
            logger.info(f"SSE subscriber {subscriber_id} disconnected")
        finally:
            # Clean up subscriber
            self.subscribers.pop(subscriber_id, None)

    async def cleanup_completed(self, older_than_hours: int = 24):
        """Clean up completed download records

        Args:
            older_than_hours: Remove completed downloads older than this
        """
        cutoff = datetime.utcnow().timestamp() - (older_than_hours * 3600)
        to_remove = []

        for download_id, status in self.active_downloads.items():
            if (
                status.status
                in [
                    DownloadState.COMPLETED,
                    DownloadState.FAILED,
                    DownloadState.CANCELLED,
                ]
                and status.completed_at
                and status.completed_at.timestamp() < cutoff
            ):
                to_remove.append(download_id)

        for download_id in to_remove:
            self.active_downloads.pop(download_id, None)
            self.download_tasks.pop(download_id, None)

        logger.info(f"Cleaned up {len(to_remove)} old download records")

    async def _download_file_task(self, download_id: str):
        """Main download task implementation"""
        status = self.active_downloads[download_id]

        try:
            async with self.semaphore:
                status.status = DownloadState.DOWNLOADING
                await self._notify_subscribers(status)

                # Build download URL
                url = f"https://huggingface.co/{status.repo_id}/resolve/main/{status.filename}"

                # Create target file path
                target_path = (
                    self.download_dir
                    / f"{status.repo_id.replace('/', '_')}_{status.filename}"
                )
                target_path.parent.mkdir(exist_ok=True, parents=True)

                # Download file
                async with aiohttp.ClientSession() as session:
                    await self._download_with_progress(
                        session, url, target_path, status
                    )

                # Mark as completed
                status.status = DownloadState.COMPLETED
                status.progress_percent = 100.0
                status.completed_at = datetime.utcnow()

                logger.info(f"Download completed: {download_id}")

        except asyncio.CancelledError:
            status.status = DownloadState.CANCELLED
            status.completed_at = datetime.utcnow()
            logger.info(f"Download cancelled: {download_id}")

        except Exception as e:
            status.status = DownloadState.FAILED
            status.error_message = str(e)
            status.completed_at = datetime.utcnow()
            logger.error(f"Download failed {download_id}: {e}")

        finally:
            await self._notify_subscribers(status)

            # Clean up task reference
            self.download_tasks.pop(download_id, None)

    async def _download_with_progress(
        self,
        session: aiohttp.ClientSession,
        url: str,
        target_path: Path,
        status: DownloadStatus,
    ):
        """Download file with progress tracking"""

        async with session.get(url) as response:
            if response.status != 200:
                raise aiohttp.ClientError(f"HTTP {response.status}: {response.reason}")

            # Get file size
            total_size = int(response.headers.get("Content-Length", 0))
            status.total_bytes = total_size if total_size > 0 else None

            # Download with progress tracking
            downloaded = 0
            chunk_size = 8192
            start_time = datetime.utcnow()
            last_update = start_time

            async with aiofiles.open(target_path, "wb") as f:
                async for chunk in response.content.iter_chunked(chunk_size):
                    await f.write(chunk)
                    downloaded += len(chunk)
                    status.bytes_downloaded = downloaded

                    # Update progress
                    if total_size > 0:
                        status.progress_percent = (downloaded / total_size) * 100

                    # Calculate speed and ETA
                    now = datetime.utcnow()
                    if (now - last_update).seconds >= 1:  # Update every second
                        elapsed = (now - start_time).total_seconds()
                        if elapsed > 0:
                            speed_bps = downloaded / elapsed
                            status.download_speed_mbps = (
                                speed_bps / 1024 / 1024
                            ) * 8  # Mbps

                            if total_size > 0 and speed_bps > 0:
                                remaining = total_size - downloaded
                                status.eta_seconds = int(remaining / speed_bps)

                        await self._notify_subscribers(status)
                        last_update = now

    def _find_existing_download(self, repo_id: str, filename: str) -> Optional[str]:
        """Find existing download for the same file"""
        for download_id, status in self.active_downloads.items():
            if (
                status.repo_id == repo_id
                and status.filename == filename
                and status.status in [DownloadState.PENDING, DownloadState.DOWNLOADING]
            ):
                return download_id
        return None

    async def _notify_subscribers(self, status: DownloadStatus):
        """Notify all SSE subscribers of status update"""
        if not self.subscribers:
            return

        # Add to all subscriber queues
        for queue in self.subscribers.values():
            try:
                await asyncio.wait_for(queue.put(status), timeout=1.0)
            except asyncio.TimeoutError:
                logger.warning("Slow SSE subscriber detected")
            except Exception as e:
                logger.error(f"Failed to notify SSE subscriber: {e}")
