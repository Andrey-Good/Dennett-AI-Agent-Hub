# Hugging Face Service Tests

This directory contains comprehensive tests for the Hugging Face service (`model_manager/core/services/huggingface_service.py`).

## Test Overview

The test suite covers the main functionality of the HuggingFaceService class:

### ✅ Passing Tests (14/14)

1. **Search Functionality (4 tests)**
   - `test_search_models_basic` - Basic model search with query, limit, offset, and sorting
   - `test_search_models_with_filters` - Search with task and license filters
   - `test_search_models_sorting_options` - Different sorting (likes, downloads, time, update)
   - `test_search_models_pagination` - Pagination with limit parameter

2. **Model Details (3 tests)**
   - `test_get_model_details_success` - Successful model metadata retrieval
   - `test_get_model_details_without_readme` - Handles missing README gracefully
   - `test_get_model_details_invalid_model` - Error handling for invalid models

3. **GGUF Provider Discovery (3 tests)**
   - `test_find_gguf_providers_found` - Finds and ranks GGUF providers
   - `test_find_gguf_providers_none` - Handles models without GGUF files
   - `test_find_gguf_providers_ranking` - Tests provider scoring algorithm

4. **Authentication & Initialization (4 tests)**
   - `test_service_without_token` - Service works without API key
   - `test_service_with_token` - Service uses provided API key
   - `test_service_initialization` - Trusted provider configuration
   - `test_service_async_context_manager` - Async session management

## Running Tests

```bash
# Run all tests
python -m pytest tests/test_huggingface_service.py -v

# Run with coverage
python -m pytest tests/test_huggingface_service.py --cov=model_manager.core.services.huggingface_service

# Run specific test
python -m pytest tests/test_huggingface_service.py::TestHuggingFaceService::test_search_models_basic -v
```

## Test Architecture

### Mocking Strategy
- Uses `pytest-mock` for comprehensive API mocking
- Mocks `HfApi` methods to avoid real API calls
- Mocks `aiohttp.ClientSession` for async operations
- Creates realistic mock objects that mimic Hugging Face model responses

### Test Data
- `fixtures/` directory contains sample API responses
- `MockHuggingFaceModel` class mimics real Hugging Face objects
- Comprehensive test data covering various scenarios

### Key Testing Concepts
- **Happy path tests** focus on successful operations (as requested)
- Mock data covers edge cases and error conditions
- Tests verify both API parameter passing and response validation
- Async operations properly tested with `@pytest.mark.asyncio`

## API Key Configuration

The tests are designed to work without requiring real Hugging Face API credentials:

```python
# No API key needed for basic functionality
service = HuggingFaceService()

# With API token (for private models)
service = HuggingFaceService(token="your-hf-token")
```

To use a real API key for testing (optional):
```bash
export HUGGINGFACE_TOKEN=your-token-here
```

## Test Coverage

The tests provide comprehensive coverage of:
- Model search with filtering and sorting
- Detailed model information retrieval
- GGUF provider discovery and ranking
- Error handling for various failure scenarios
- Authentication token handling
- Async context management

All tests pass successfully and provide a robust foundation for ongoing development.