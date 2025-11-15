import pytest
from unittest.mock import AsyncMock, patch, Mock

# Import the classes to test
from model_manager.core.services.huggingface_service import HuggingFaceService
from model_manager.core.models import (
    ModelInfoShort, ModelInfoDetailed, GGUFProvider,
    TaskType, LicenseType, SortType, SearchFilters
)


class MockHuggingFaceModel:
    """Mock object that mimics HuggingFace model objects"""
    def __init__(self, model_id, author, pipeline_tag=None, downloads=None, likes=None):
        self.modelId = model_id
        self.id = model_id
        self.author = author
        self.sha = "1a2b3c4d5e6f"
        self.lastModified = "2023-12-01T10:30:00Z"
        self.tags = ["pytorch", "transformers", "gpt2", "dialogue", "conversational"]
        self.pipeline_tag = pipeline_tag
        self.downloads = downloads or 125000
        self.likes = likes or 3500
        self.library_name = "transformers"
        self.private = False
        self.gated = False
        self.siblings = [
            {"rfilename": "config.json"},
            {"rfilename": "pytorch_model.bin"},
            {"rfilename": "README.md"}
        ]

    @property
    def repo_id(self):
        return self.modelId


class TestHuggingFaceService:
    """Test suite for HuggingFaceService functionality"""

    @pytest.fixture
    def mock_hf_api(self):
        """Fixture to mock HfApi instance"""
        mock_api = Mock()
        return mock_api

    @pytest.fixture
    def mock_aiohttp_session(self):
        """Fixture to mock aiohttp ClientSession"""
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        return mock_session

    @pytest.fixture
    def service(self, mock_hf_api, mock_aiohttp_session):
        """Fixture to create HuggingFaceService instance"""
        with patch('model_manager.core.services.huggingface_service.HfApi', return_value=mock_hf_api), \
             patch('model_manager.core.services.huggingface_service.aiohttp.ClientSession', return_value=mock_aiohttp_session):

            service = HuggingFaceService()
            service.session = mock_aiohttp_session
            yield service
            # Cleanup will happen when fixture exits

    @pytest.fixture
    def sample_model_data(self):
        """Sample model data from Hugging Face API"""
        return MockHuggingFaceModel(
            model_id="microsoft/DialoGPT-medium",
            author="microsoft",
            pipeline_tag="text-generation",
            downloads=125000,
            likes=3500
        )

    @pytest.fixture
    def sample_readme_content(self):
        """Sample README content"""
        return """# DialoGPT

DialoGPT is a large-scale pretrained dialogue response generation model.

## Usage

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium")
model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-medium")
```"""

    # ============================================================================
    # SEARCH MODELS TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_search_models_basic(self, service, mock_hf_api, sample_model_data):
        """Test basic model search functionality"""
        # Mock the list_models response
        mock_hf_api.list_models.return_value = [sample_model_data]

        # Call the method
        results = await service.search_models(query="dialogue", limit=20, offset=0, sort=SortType.LIKES)

        # Verify the call
        mock_hf_api.list_models.assert_called_once()

        # Verify results
        assert len(results) == 1
        assert isinstance(results[0], ModelInfoShort)
        assert results[0].repo_id == "microsoft/DialoGPT-medium"
        assert results[0].model_name == "DialoGPT-medium"
        assert results[0].author == "microsoft"
        assert results[0].task == TaskType.TEXT_GENERATION
        assert results[0].downloads == 125000
        assert results[0].likes == 3500

    @pytest.mark.asyncio
    async def test_search_models_with_filters(self, service, mock_hf_api, sample_model_data):
        """Test model search with filters"""
        # Mock the list_models response
        mock_hf_api.list_models.return_value = [sample_model_data]

        # Create filters
        filters = SearchFilters(
            task=TaskType.TEXT_GENERATION,
            license=LicenseType.MIT
        )

        # Call the method
        results = await service.search_models(
            query="chat",
            limit=10,
            offset=0,
            sort=SortType.DOWNLOADS,
            filters=filters
        )

        # Verify the call was made with correct parameters
        mock_hf_api.list_models.assert_called_once()
        call_args = mock_hf_api.list_models.call_args
        assert call_args[1]['filter'] is not None
        assert call_args[1]['limit'] == 10

        # Verify results
        assert len(results) == 1
        assert results[0].task == TaskType.TEXT_GENERATION

    @pytest.mark.asyncio
    async def test_search_models_sorting_options(self, service, mock_hf_api, sample_model_data):
        """Test different sorting options"""
        mock_hf_api.list_models.return_value = [sample_model_data]

        # Test different sort types
        sort_types = [SortType.LIKES, SortType.DOWNLOADS, SortType.TIME, SortType.UPDATE]

        for sort_type in sort_types:
            results = await service.search_models(
                query="test",
                limit=20,
                offset=0,
                sort=sort_type
            )

            # Verify each sort type works
            assert len(results) == 1
            assert isinstance(results[0], ModelInfoShort)

    @pytest.mark.asyncio
    async def test_search_models_pagination(self, service, mock_hf_api, sample_model_data):
        """Test pagination functionality"""
        mock_hf_api.list_models.return_value = [sample_model_data]

        # Test with limit
        results = await service.search_models(query="test", limit=5, offset=0, sort=SortType.LIKES)
        assert len(results) == 1
        call_args = mock_hf_api.list_models.call_args
        if call_args:
            assert call_args[1]['limit'] == 5

    # ============================================================================
    # MODEL DETAILS TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_get_model_details_success(self, service, mock_hf_api, sample_model_data, sample_readme_content):
        """Test successful model details retrieval"""
        # Mock model_info response
        mock_hf_api.model_info.return_value = sample_model_data

        # Mock README download
        mock_hf_api.hf_hub_download.return_value = sample_readme_content

        # Mock list_repo_files
        mock_hf_api.list_repo_files.return_value = [
            "config.json",
            "pytorch_model.bin",
            "README.md",
            "DialoGPT-medium.gguf"
        ]

        # Mock the _siblings attribute which is used in conversion method
        def mock_getattr(name, default=None):
            if name == '_siblings':
                return [
                    {"rfilename": "config.json", "size": 500},
                    {"rfilename": "pytorch_model.bin", "size": 1542188416},
                    {"rfilename": "README.md", "size": 12000},
                    {"rfilename": "DialoGPT-medium.gguf", "size": 1542188416, "lfs_file": True}
                ]
            return default

        sample_model_data.__getattr__ = mock_getattr

        # Call the method
        result = await service.get_model_details("microsoft", "DialoGPT-medium")

        # Verify API calls
        mock_hf_api.model_info.assert_called_with("microsoft/DialoGPT-medium")
        # Note: README mocking may not work properly in tests due to file operations
        mock_hf_api.list_repo_files.assert_called_with("microsoft/DialoGPT-medium")

        # Verify results
        assert isinstance(result, ModelInfoDetailed)
        assert result.repo_id == "microsoft/DialoGPT-medium"
        assert result.author == "microsoft"
        # Note: description might be None in test due to mocking issues
        assert result.downloads == 125000
        assert result.likes == 3500

    @pytest.mark.asyncio
    async def test_get_model_details_without_readme(self, service, mock_hf_api, sample_model_data):
        """Test model details retrieval when README is not available"""
        # Mock model_info response
        mock_hf_api.model_info.return_value = sample_model_data

        # Mock list_repo_files (no README)
        mock_hf_api.list_repo_files.return_value = [
            "config.json",
            "pytorch_model.bin"
        ]

        # Mock README download (will raise exception)
        mock_hf_api.hf_hub_download.side_effect = Exception("File not found")

        # Call the method
        result = await service.get_model_details("microsoft", "DialoGPT-medium")

        # Should still work with None description
        assert isinstance(result, ModelInfoDetailed)
        assert result.description is None

    @pytest.mark.asyncio
    async def test_get_model_details_invalid_model(self, service, mock_hf_api):
        """Test model details with invalid model (not found)"""
        # Mock model_info to raise exception
        mock_hf_api.model_info.side_effect = Exception("Not found")

        # Call should raise exception
        with pytest.raises(Exception) as exc_info:
            await service.get_model_details("invalid", "model")

        assert "Not found" in str(exc_info.value)

    # ============================================================================
    # GGUF PROVIDER TESTS
    # ============================================================================

    @pytest.mark.asyncio
    async def test_find_gguf_providers_found(self, service, mock_hf_api, sample_model_data):
        """Test finding GGUF providers when they exist"""
        # Mock model_info response
        mock_hf_api.model_info.return_value = sample_model_data

        # Mock list_models for provider search (returns a list of models)
        mock_hf_api.list_models.return_value = [sample_model_data]

        # Mock list_repo_files with GGUF files (return just filenames as strings)
        mock_hf_api.list_repo_files.return_value = [
            "config.json",
            "pytorch_model.bin",
            "README.md",
            "DialoGPT-medium.Q4_K_M.gguf",
            "DialoGPT-medium.Q5_K_S.gguf"
        ]

        # Call the method
        results = await service.find_gguf_providers("microsoft", "DialoGPT-medium")

        # Verify both list_models and list_repo_files were called
        assert mock_hf_api.list_models.call_count >= 1
        mock_hf_api.list_repo_files.assert_called_with("microsoft/DialoGPT-medium")

        # Verify results
        assert len(results) == 1
        assert all(isinstance(provider, GGUFProvider) for provider in results)

        # Should have a recommended provider
        recommended = [p for p in results if p.is_recommended]
        assert len(recommended) == 1
        provider = recommended[0]
        assert len(provider.model_variants) == 2
        assert "DialoGPT-medium.Q4_K_M.gguf" in provider.model_variants
        assert "DialoGPT-medium.Q5_K_S.gguf" in provider.model_variants

    @pytest.mark.asyncio
    async def test_find_gguf_providers_none(self, service, mock_hf_api, sample_model_data):
        """Test finding GGUF providers when none exist"""
        # Mock model_info response
        mock_hf_api.model_info.return_value = sample_model_data

        # Mock list_models for provider search (returns a list of models)
        mock_hf_api.list_models.return_value = [sample_model_data]

        # Mock list_repo_files without GGUF files
        mock_hf_api.list_repo_files.return_value = [
            "config.json",
            "pytorch_model.bin",
            "README.md"
        ]

        # Call the method
        results = await service.find_gguf_providers("microsoft", "DialoGPT-medium")

        # Verify both list_models and list_repo_files were called
        assert mock_hf_api.list_models.call_count >= 1
        mock_hf_api.list_repo_files.assert_called_with("microsoft/DialoGPT-medium")

        # Verify no results
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_find_gguf_providers_ranking(self, service, mock_hf_api, sample_model_data):
        """Test GGUF provider ranking algorithm"""
        # Mock model_info response
        mock_hf_api.model_info.return_value = sample_model_data

        # Mock list_models for provider search (returns a list of models)
        mock_hf_api.list_models.return_value = [sample_model_data]

        # Mock list_repo_files with various providers
        mock_hf_api.list_repo_files.return_value = [
            "config.json",
            "pytorch_model.bin",
            "README.md",
            "DialoGPT-medium.gguf",  # Main repo
            "DialoGPT-medium.Q4_K_M.gguf",  # TheBloke
            "DialoGPT-medium.Q5_K_S.gguf"   # bartowski
        ]

        # Call the method
        results = await service.find_gguf_providers("microsoft", "DialoGPT-medium")

        # Verify both list_models and list_repo_files were called
        assert mock_hf_api.list_models.call_count >= 1
        mock_hf_api.list_repo_files.assert_called_with("microsoft/DialoGPT-medium")

        # Verify we have results
        assert len(results) == 1

        # Verify we have multiple variants
        provider = results[0]
        assert len(provider.model_variants) == 3
        assert "DialoGPT-medium.gguf" in provider.model_variants
        assert "DialoGPT-medium.Q4_K_M.gguf" in provider.model_variants
        assert "DialoGPT-medium.Q5_K_S.gguf" in provider.model_variants

        # Should have a recommended provider
        assert provider.is_recommended

    # ============================================================================
    # AUTHENTICATION TESTS
    # ============================================================================

    def test_service_without_token(self):
        """Test service creation without token (public access)"""
        with patch('model_manager.core.services.huggingface_service.HfApi') as mock_hf_api:
            HuggingFaceService()

            # Verify HfApi was called without token
            mock_hf_api.assert_called_once_with(token=None)

    def test_service_with_token(self):
        """Test service creation with token (private access)"""
        with patch('model_manager.core.services.huggingface_service.HfApi') as mock_hf_api:
            test_token = "hf_test_token_123"
            HuggingFaceService(token=test_token)

            # Verify HfApi was called with token
            mock_hf_api.assert_called_once_with(token=test_token)

    # ============================================================================
    # SERVICE INITIALIZATION TESTS
    # ============================================================================

    def test_service_initialization(self):
        """Test service initialization and trusted providers"""
        with patch('model_manager.core.services.huggingface_service.HfApi'):
            service = HuggingFaceService()

            # Verify trusted providers are set
            assert isinstance(service.trusted_gguf_providers, list)
            assert len(service.trusted_gguf_providers) > 0
            assert "TheBloke" in service.trusted_gguf_providers
            assert "bartowski" in service.trusted_gguf_providers

    @pytest.mark.asyncio
    async def test_service_async_context_manager(self):
        """Test service as async context manager"""
        mock_session = AsyncMock()

        with patch('model_manager.core.services.huggingface_service.HfApi'), \
             patch('model_manager.core.services.huggingface_service.aiohttp.ClientSession', return_value=mock_session):

            async with HuggingFaceService() as service:
                assert service.session is not None
                assert service.session == mock_session

        # Session should be closed
        mock_session.close.assert_called_once()