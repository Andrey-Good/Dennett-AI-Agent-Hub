import aiohttp
from typing import List, Optional
from huggingface_hub import HfApi  # type: ignore
import logging
from apps.ai_core.ai_core.db.models import (
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
        from apps.ai_core.ai_core.config.settings import config

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
        """Search for models on Hugging Face Hub

        Args:
            query: Search query string
            limit: Maximum number of results
            offset: Results offset for pagination
            sort: Sort order
            filters: Optional search filters

        Returns:
            List of ModelInfoShort objects

        Raises:
            aiohttp.ClientError: If HF API request fails
        """
        try:
            logger.info(
                f"Searching models: query='{query}', limit={limit}, offset={offset}"
            )

            # Convert our enums to HF API format

            # Build HF ModelFilter parameters
            task_filter = filters.task.value if filters and filters.task else None
            tags_filter = filters.tags if filters and filters.tags else None

            # Create filter dictionary with supported parameters only
            filter_dict = {}
            if task_filter:
                filter_dict["task"] = task_filter
            if tags_filter:
                filter_dict["tags"] = tags_filter  # type: ignore[assignment]

            direction = "desc"  # Default direction for sorting
            direction_value = -1 if direction == "desc" else 1

            # Search models using HfApi
            models = self.hf_api.list_models(
                search=query,
                filter=filter_dict if filter_dict else None,
                sort=sort.value,
                direction=direction_value,
                limit=limit,
            )

            # Convert to our models and apply offset
            results: List[ModelInfoShort] = []
            for i, model in enumerate(models):
                if i < offset:
                    continue
                if len(results) >= limit:
                    break

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
        """Get detailed information about a specific model

        Args:
            author: Model author/organization
            model_name: Model name

        Returns:
            ModelInfoDetailed object

        Raises:
            aiohttp.ClientError: If model not found or API error
        """
        repo_id = f"{author}/{model_name}"

        try:
            logger.info(f"Getting model details for {repo_id}")

            # Get model info from HF API
            model_info = self.hf_api.model_info(repo_id)

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
        """Find and rank GGUF providers for a model

        Args:
            author: Original model author
            model_name: Original model name

        Returns:
            List of GGUFProvider objects, sorted by recommendation
        """
        base_repo_id = f"{author}/{model_name}"

        try:
            logger.info(f"Finding GGUF providers for {base_repo_id}")

            # Search for GGUF versions
            search_queries = [
                f"{model_name} GGUF",
                f"{author} {model_name} GGUF",
                f"TheBloke {model_name} GGUF",
            ]

            providers = []
            seen_repos = set()

            for query in search_queries:
                models = self.hf_api.list_models(search=query, limit=50)

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
            # Try to get README file
            files = self.hf_api.list_repo_files(repo_id)
            readme_files = [f for f in files if f.lower().startswith("readme")]

            if not readme_files:
                return None

            # Get the first README file content
            readme_file = readme_files[0]
            content = self.hf_api.hf_hub_download(
                repo_id=repo_id, filename=readme_file, repo_type="model"
            )

            with open(content, "r", encoding="utf-8") as f:
                return f.read()

        except Exception as e:
            logger.warning(f"Could not get README for {repo_id}: {e}")
            return None

    async def _has_gguf_files(self, repo_id: str) -> bool:
        """Check if repository contains GGUF files"""
        try:
            files = self.hf_api.list_repo_files(repo_id)
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
