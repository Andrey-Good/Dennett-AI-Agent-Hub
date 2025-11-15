## Backend to AI Core Migration Plan

| Old Path                                                    | New Path                                                          | Notes                               |
| ----------------------------------------------------------- | ----------------------------------------------------------------- | ----------------------------------- |
| `backend/`                                                  | `apps/ai-core/`                                                   | Root directory of the AI Core app.  |
| `backend/model_manager/`                                    | `apps/ai-core/ai_core/`                                           | Main application package.           |
| `backend/model_manager/app/main.py`                         | `apps/ai-core/ai_core/main.py`                                    | Application entry point.            |
| `backend/model_manager/app/__init__.py`                     | `apps/ai-core/ai_core/__init__.py`                                |                                     |
| `backend/model_manager/core/config/settings.py`             | `apps/ai-core/ai_core/config/settings.py`                         | Application settings.               |
| `backend/model_manager/core/services/download_manager.py`   | `apps/ai-core/ai_core/services/download_manager.py`               | Download manager service.           |
| `backend/model_manager/core/services/huggingface_service.py`| `apps/ai-core/ai_core/services/huggingface_service.py`            | Hugging Face service.               |
| `backend/model_manager/core/services/local_storage.py`      | `apps/ai-core/ai_core/services/local_storage.py`                  | Local storage service.              |
| `backend/model_manager/core/models.py`                      | `apps/ai-core/ai_core/models.py`                                  | Pydantic models.                    |
| `backend/tests/`                                            | `apps/ai-core/tests/`                                             | Tests for the AI Core app.          |
| `backend/requirements.txt`                                  | `apps/ai-core/requirements.txt`                                   | Python dependencies.                |
| `backend/requirements-dev.txt`                              | `apps/ai-core/requirements-dev.txt`                               | Python dev dependencies.            |
| `backend/env.template`                                      | `apps/ai-core/env.template`                                       | Environment variable template.      |
| `backend/start.sh`                                          | `apps/ai-core/start.sh`                                           | Start script.                       |
| `backend/CLAUDE.md`                                         | `apps/ai-core/CLAUDE.md`                                          | Documentation.                      |
| `backend/.claude/`                                          | `apps/ai-core/.claude/`                                           | Claude settings.                    |
