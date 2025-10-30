# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Manager service for the Dennet AI platform. It provides a comprehensive API for managing AI model lifecycles, including searching models from Hugging Face Hub, downloading models with progress tracking, and managing local model storage.

## Architecture

### Core Components

1. **FastAPI Application** (`model_manager/app/main.py`)
   - RESTful API with OAuth2 Bearer token authentication
   - CORS middleware enabled for cross-origin requests
   - Structured error handling with custom error responses

2. **Service Layer** (`model_manager/core/services/`)
   - `huggingface_service.py`: Hugging Face Hub integration for model discovery and metadata retrieval
   - `download_manager.py`: Async download management with progress tracking and Server-Sent Events
   - `local_storage.py`: Local file system management for imported models and metadata

3. **Models** (`model_manager/core/models.py`)
   - Pydantic models for API contracts and data validation
   - Comprehensive type definitions for model metadata, downloads, and local storage

### Key Features

- **Model Discovery**: Search and filter models from Hugging Face Hub with sorting and pagination
- **GGUF Integration**: Find and rank GGUF format providers for specific models
- **Async Downloads**: Background downloading with real-time progress updates via SSE
- **Local Management**: Import, validate, and manage locally stored GGUF files
- **Storage Management**: Cleanup utilities and storage statistics

## Development Commands

### Setup and Installation
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Linux/Mac)
source .venv/bin/activate

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p models downloads logs

# Create environment file from template
cp env.template .env
# Edit .env with your configuration
```

### Running the Application
```bash
# Using the startup script (recommended)
./start.sh

# Or run directly with uvicorn
python -m uvicorn model_manager.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Testing
```bash
# Run tests with pytest
python -m pytest

# Run with verbose output
python -m pytest -v

# Run test with coverage
python -m pytest --cov=model_manager
```

### Linting and Code Quality
```bash
# The project uses standard Python code quality patterns
# Ensure PEP 8 compliance in all code
# Use type hints consistently (already implemented throughout)
```

## Configuration

The application uses environment variables configured via `.env` file. Key configurations:

- `MODEL_MANAGER_API_TOKEN`: Secure API token for authentication
- `MAX_CONCURRENT_DOWNLOADS`: Number of parallel downloads (default: 3)
- `MODELS_DIR`/`DOWNLOADS_DIR`: Storage directories
- `LOG_LEVEL`: Logging verbosity level

## API Structure

### Authentication
All endpoints require Bearer token authentication via `Authorization: Bearer <token>` header.

### Main Endpoints

**Hub Operations:**
- `GET /hub/search` - Search models with filtering and pagination
- `GET /hub/model/{author}/{model_name}` - Get detailed model information
- `GET /hub/model/{author}/{model_name}/gguf-providers` - Find GGUF format providers

**Local Downloads:**
- `POST /local/download` - Start asynchronous download
- `GET /local/download/status` - SSE stream for download progress
- `DELETE /local/download/{download_id}` - Cancel ongoing download

**Local Model Management:**
- `POST /local/import` - Import local GGUF files
- `GET /local/models` - List all local models
- `GET /local/models/{model_id}` - Get specific model details
- `DELETE /local/models/{model_id}` - Delete model from storage

**Utilities:**
- `GET /local/storage/stats` - Storage usage statistics
- `POST /local/storage/cleanup` - Cleanup orphaned files

### Error Handling
The API uses structured error responses with error codes:
- `INVALID_TOKEN`: Authentication failure
- `NOT_FOUND`: Resource not found
- `SERVICE_UNAVAILABLE`: External service issues
- `INTERNAL_ERROR`: Server-side errors

## Dependencies

### Core Dependencies
- **FastAPI**: Web framework with automatic API documentation
- **Uvicorn**: ASGI server for production development
- **Pydantic**: Data validation and serialization
- **HuggingFace Hub**: Model discovery and metadata
- **Transformers**: Model handling and conversion support
- **aiohttp/aiofiles**: Asynchronous HTTP and file operations

### Development Dependencies
- **pytest**: Testing framework
- **pytest-asyncio**: Async test support
- **httpx**: HTTP client for testing

## Development Notes

### Code Structure
- All business logic is encapsulated in service classes
- Async/await pattern throughout for non-blocking operations
- Type hints used consistently for better code maintainability
- JSON-based logging for structured logging output

### File Organization
- API routes in `model_manager/app/main.py`
- Service classes in `model_manager/core/services/`
- Data models in `model_manager/core/models.py`
- Configuration in `model_manager/core/config/`

### Best Practices
- Always handle async operations with proper error handling
- Use dependency injection for service instantiation
- Follow REST conventions for endpoint design
- Implement proper authentication and authorization
- Use structured logging for debugging and monitoring