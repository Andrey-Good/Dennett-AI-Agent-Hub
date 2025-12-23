# apps/ai_core/ai_core/logic/atomic_write.py
"""
Atomic JSON file writing utility.

Provides a crash-safe method to write JSON files using atomic operations
with proper fsync to ensure data is persisted to disk.
"""

import json
import os
import logging
from uuid import uuid4
from typing import Any, Dict

logger = logging.getLogger(__name__)


def atomic_write_json(file_path: str, data: Dict[str, Any]) -> None:
    """
    Atomically write JSON data to a file.

    This function ensures crash-safety by:
    1. Writing to a temporary file in the same directory
    2. Flushing application buffer
    3. Calling fsync to persist to disk
    4. Atomically replacing the target file
    5. (POSIX only) Fsyncing the directory for durability

    Args:
        file_path: Absolute path to the target JSON file
        data: Dictionary to serialize as JSON

    Raises:
        OSError: If file operations fail
        TypeError: If data is not JSON-serializable
    """
    # Get directory and ensure it exists
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    # Create temporary file path in same directory (required for atomic rename)
    tmp_path = f"{file_path}.tmp.{uuid4().hex}"

    try:
        # Write to temporary file
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            # Flush application buffer
            f.flush()
            # CRITICAL: Sync OS buffer to physical disk
            os.fsync(f.fileno())

        # Atomic replace (works on both Windows and POSIX)
        os.replace(tmp_path, file_path)

        # POSIX-only: fsync directory to ensure rename is durable
        # This is best-effort - don't fail if it doesn't work
        if os.name == 'posix':
            _fsync_directory(dir_name)

        logger.debug(f"Atomically wrote JSON to {file_path}")

    except Exception as e:
        # Clean up temp file if it exists
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise


def _fsync_directory(dir_path: str) -> None:
    """
    Fsync a directory to ensure metadata changes (like renames) are durable.

    This is a POSIX-only operation and is best-effort - errors are logged
    but do not cause the write operation to fail.

    Args:
        dir_path: Path to directory to fsync
    """
    if not dir_path:
        dir_path = '.'

    try:
        dir_fd = os.open(dir_path, os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except (OSError, AttributeError) as e:
        # AttributeError: O_DIRECTORY might not exist on some systems
        # OSError: fsync might fail on some filesystems
        logger.debug(f"Directory fsync not supported or failed for {dir_path}: {e}")


def read_json_file(file_path: str) -> Dict[str, Any]:
    """
    Read and parse a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Parsed JSON data as dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
