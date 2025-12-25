import aiohttp
import asyncio
from typing import List, Optional
from huggingface_hub import HfApi  # type: ignore
import logging

try:
    from apps.ai_core.ai_core.db.models import (
        ModelInfoShort,
        ModelInfoDetailed,
        GGUFProvider,
        SearchFilters,
        TaskType,
        SortType,
    )
except ModuleNotFoundError:
    from ai_core.db.models import (
        ModelInfoShort,
        ModelInfoDetailed,
        GGUFProvider,
        SearchFilters,
        TaskType,
        SortType,
    )

logger = logging.getLogger(__name__)


class HuggingFaceService:
    """Service for interacting with Hugging Face Hub API"""

    def __init__(self, token: Optional[str] = None):
        """Initialize HuggingFace service

        Args:
            token: Optional HF API token for authenticated requests
        """
        try:
            from apps.ai_core.ai_core.config.settings import config
        except ModuleNotFoundError:
            from ai_core.config.settings import config

        # Use config token if not provided
        if token is None:
            token = config.hf_token

        self.hf_api = HfApi(token=token)
        self.session: Optional[aiohttp.ClientSession] = None

        # Use trusted GGUF providers from configuration
        self.trusted_gguf_providers = config.trusted_gguf_providers

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def search_models(
            self,
            query: str,
            limit: int = 20,
            offset: int = 0,
            sort: SortType = SortType.LIKES,
            filters: Optional[SearchFilters] = None,
    ) -> List[ModelInfoShort]:
        """Search for models on Hugging Face Hub"""
        try:
            logger.info(f"Searching models: query='{query}', limit={limit}, offset={offset}")

            # Build filter dict
            task_filter = filters.task.value if filters and filters.task else None
            tags_filter = filters.tags if filters and filters.tags else None

            filter_dict = {}
            if task_filter:
                filter_dict["task"] = task_filter
            if tags_filter:
                filter_dict["tags"] = tags_filter

            direction_value = -1  # desc

            # Run blocking HF API call in thread pool
            models = await asyncio.wait_for(
                asyncio.to_thread(
                    self.hf_api.list_models,
                    search=query,
                    filter=filter_dict if filter_dict else None,
                    sort=sort.value,
                    direction=direction_value,
                    limit=limit + offset,
                ),
                timeout=30.0
            )

            # Convert to list and apply offset/limit
            model_list = list(models)[offset:offset + limit]

            results: List[ModelInfoShort] = []
            for model in model_list:
                model_info = await self._convert_to_model_info_short(model)
                results.append(model_info)

            logger.info(f"Found {len(results)} models")
            return results

        except Exception as e:
            logger.error(f"Failed to search models: {e}")
            raise

    async def get_model_details(
            self, author: str, model_name: str
    ) -> ModelInfoDetailed:
        repo_id = f"{author}/{model_name}"

        try:
            logger.info(f"Getting model details for {repo_id}")

            # FIX: Wrap blocking call
            model_info = await asyncio.to_thread(
                self.hf_api.model_info,
                repo_id
            )

            # Get README content
            readme_content = await self._get_model_readme(repo_id)

            # Convert to our detailed model
            detailed_model = await self._convert_to_model_info_detailed(
                model_info, readme_content
            )

            logger.info(f"Retrieved details for {repo_id}")
            return detailed_model

        except Exception as e:
            logger.error(f"Failed to get model details for {repo_id}: {e}")
            raise

    async def find_gguf_providers(
            self, author: str, model_name: str
    ) -> List[GGUFProvider]:
        base_repo_id = f"{author}/{model_name}"

        try:
            logger.info(f"Finding GGUF providers for {base_repo_id}")

            search_queries = [
                f"{model_name} GGUF",
                f"{author} {model_name} GGUF",
                f"TheBloke {model_name} GGUF",
            ]

            providers = []
            seen_repos = set()

            for query in search_queries:
                # FIX: Wrap blocking call
                models = await asyncio.to_thread(
                    self.hf_api.list_models,
                    search=query,
                    limit=50
                )

                for model in models:
                    if model.modelId in seen_repos:
                        continue

                    # Check if this repo contains GGUF files
                    if await self._has_gguf_files(model.modelId):
                        provider = await self._convert_to_gguf_provider(
                            model, base_repo_id
                        )
                        providers.append(provider)
                        seen_repos.add(model.modelId)

            # Sort providers by recommendation score
            providers.sort(key=self._calculate_provider_score, reverse=True)

            # Mark top provider as recommended
            if providers:
                providers[0].is_recommended = True

            logger.info(f"Found {len(providers)} GGUF providers")
            return providers

        except Exception as e:
            logger.error(f"Failed to find GGUF providers for {base_repo_id}: {e}")
            raise

    async def _get_model_readme(self, repo_id: str) -> Optional[str]:
        """Get README content for a model"""
        try:
            # FIX: Wrap blocking calls
            files = await asyncio.to_thread(
                self.hf_api.list_repo_files,
                repo_id
            )

            readme_files = [f for f in files if f.lower().startswith("readme")]
            if not readme_files:
                return None

            readme_file = readme_files[0]
            content_path = await asyncio.to_thread(
                self.hf_api.hf_hub_download,
                repo_id=repo_id,
                filename=readme_file,
                repo_type="model"
            )

            # File reading is also blocking
            def read_file():
                with open(content_path, "r", encoding="utf-8") as f:
                    return f.read()

            return await asyncio.to_thread(read_file)

        except Exception as e:
            logger.warning(f"Could not get README for {repo_id}: {e}")
            return None

    async def _has_gguf_files(self, repo_id: str) -> bool:
        """Check if repository contains GGUF files"""
        try:
            # FIX: Wrap blocking call
            files = await asyncio.to_thread(
                self.hf_api.list_repo_files,
                repo_id
            )
            return any(f.endswith(".gguf") for f in files)
        except Exception:
            return False

    async def _convert_to_model_info_short(self, hf_model) -> ModelInfoShort:
        """Convert HF model to ModelInfoShort"""
        parts = hf_model.modelId.split("/", 1)
        author = parts[0] if len(parts) > 1 else "unknown"
        model_name = parts[1] if len(parts) > 1 else hf_model.modelId

        # Map HF task to our TaskType enum
        task = None
        if hasattr(hf_model, "pipeline_tag") and hf_model.pipeline_tag:
            try:
                task = TaskType(hf_model.pipeline_tag)
            except ValueError:
                pass

        return ModelInfoShort(
            repo_id=hf_model.modelId,
            model_name=model_name,
            author=author,
            task=task,
            license=None,
            downloads=getattr(hf_model, "downloads", 0),
            likes=getattr(hf_model, "likes", 0),
            last_modified=getattr(hf_model, "lastModified", None),
            tags=list(getattr(hf_model, "tags", [])),
        )

    async def _convert_to_model_info_detailed(
        self, hf_model, readme_content: Optional[str]
    ) -> ModelInfoDetailed:
        """Convert HF model to ModelInfoDetailed"""
        parts = hf_model.modelId.split("/", 1)
        author = parts[0] if len(parts) > 1 else "unknown"
        model_name = parts[1] if len(parts) > 1 else hf_model.modelId

        # Map task type
        task = None
        if hasattr(hf_model, "pipeline_tag") and hf_model.pipeline_tag:
            try:
                task = TaskType(hf_model.pipeline_tag)
            except ValueError:
                pass

        # Calculate total size
        total_size = 0
        if hasattr(hf_model, "siblings"):
            total_size = sum(
                getattr(sibling, "size", 0) or 0 for sibling in hf_model.siblings
            )

        return ModelInfoDetailed(
            repo_id=hf_model.modelId,
            model_name=model_name,
            author=author,
            task=task,
            license=None,
            downloads=getattr(hf_model, "downloads", 0),
            likes=getattr(hf_model, "likes", 0),
            last_modified=getattr(hf_model, "lastModified", None),
            tags=list(getattr(hf_model, "tags", [])),
            description=None,
            readme_content=readme_content,
            model_card=None,
            file_count=len(getattr(hf_model, "siblings", [])),
            total_size_bytes=total_size if total_size > 0 else None,
        )

    async def _convert_to_gguf_provider(
        self, hf_model, original_repo_id: str
    ) -> GGUFProvider:
        """Convert HF model to GGUFProvider"""
        parts = hf_model.modelId.split("/", 1)
        provider_name = parts[0] if len(parts) > 1 else "unknown"

        # Get GGUF file variants
        try:
            files = self.hf_api.list_repo_files(hf_model.modelId)
            gguf_files = [f for f in files if f.endswith(".gguf")]
        except Exception as e:
            logger.warning(f"Could not list repo files for {hf_model.modelId}: {e}")
            gguf_files = []

        return GGUFProvider(
            repo_id=hf_model.modelId,
            provider_name=provider_name,
            model_variants=gguf_files,
            is_recommended=False,  # Will be set later
            total_downloads=getattr(hf_model, "downloads", 0),
            last_updated=getattr(hf_model, "lastModified", None),
        )

    def _calculate_provider_score(self, provider: GGUFProvider) -> float:
        """Calculate recommendation score for GGUF provider"""
        score = 0.0

        # Trusted provider bonus
        if provider.provider_name in self.trusted_gguf_providers:
            score += 100.0

        # TheBloke gets extra bonus (most popular GGUF provider)
        if provider.provider_name == "TheBloke":
            score += 50.0

        # Download count (normalized)
        score += min(provider.total_downloads / 1000, 50.0)

        # Number of variants available
        score += min(len(provider.model_variants) * 2, 20.0)

        return score

    def _convert_sort_to_hf(self, sort: SortType) -> str:
        """Convert our SortType to HF API sort parameter"""
        mapping = {
            SortType.LIKES: "likes",
            SortType.DOWNLOADS: "downloads",
            SortType.TIME: "createdAt",
            SortType.UPDATE: "lastModified",
        }
        return mapping.get(sort, "likes")
