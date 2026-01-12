# Dennett API Documentation

Complete API reference for frontend integration with Dennett backend services.

## Services Overview

| Service | Base URL | Description |
|---------|----------|-------------|
| **ai_core** | `http://127.0.0.1:8000` | Main API: models, agents, storage, settings |
| **agent_system** | `http://127.0.0.1:8001` | Execution engine: run agents, inference streaming |

## Quick Start

### Running the Backend

```bash
# Terminal 1: ai_core
cd apps/ai_core
python -m uvicorn ai_core.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: agent_system
cd apps/agent_system
python -m uvicorn dennett.api.server:app --host 127.0.0.1 --port 8001 --reload
```

### Authentication

Currently disabled. Bearer token authentication is available but commented out.

## Documentation Structure

### ai_core API (Main Service)

| File | Endpoints | Description |
|------|-----------|-------------|
| [hub.md](./ai_core/hub.md) | `/hub/*` | HuggingFace Hub search, model details |
| [downloads.md](./ai_core/downloads.md) | `/local/download/*` | Download management with SSE |
| [local-models.md](./ai_core/local-models.md) | `/local/models/*` | Local models CRUD |
| [storage.md](./ai_core/storage.md) | `/local/*` | Storage management, import |
| [agents.md](./ai_core/agents.md) | `/agents/*` | Agents CRUD, versions, drafts, runs |
| [triggers.md](./ai_core/triggers.md) | `/triggers/*` | Trigger management |
| [settings.md](./ai_core/settings.md) | `/admin/settings/*` | Application settings |

### agent_system API (Execution Engine)

| File | Endpoints | Description |
|------|-----------|-------------|
| [executions.md](./agent_system/executions.md) | `/executions/*` | Agent execution management |
| [inference.md](./agent_system/inference.md) | `/inference/*` | Model inference + WebSocket streaming |

### Reference

| File | Description |
|------|-------------|
| [typescript-interfaces.md](./typescript-interfaces.md) | TypeScript type definitions |
| [error-handling.md](./error-handling.md) | Error codes and handling patterns |

## Endpoint Summary

### ai_core (40+ endpoints)

```
GET    /health                              Health check

GET    /hub/search                          Search models
GET    /hub/model/{author}/{name}           Model details
GET    /hub/model/{author}/{name}/gguf-providers  GGUF providers

POST   /local/download                      Start download
GET    /local/download/status               SSE download progress
DELETE /local/download/{id}                 Cancel download

GET    /local/models                        List local models
GET    /local/models/{id}                   Get model
DELETE /local/models/{id}                   Delete model

POST   /local/import                        Import GGUF file
GET    /local/storage/stats                 Storage statistics
POST   /local/storage/cleanup               Cleanup orphaned files

GET    /agents                              List agents
POST   /agents                              Create agent
GET    /agents/{id}                         Get agent
PUT    /agents/{id}                         Update agent
DELETE /agents/{id}                         Delete agent
POST   /agents/{id}/activate                Activate triggers
POST   /agents/{id}/deactivate              Deactivate triggers
GET    /agents/{id}/versions                List versions
POST   /agents/{id}/drafts                  Create draft
GET    /agents/{id}/drafts/{draft_id}       Get draft
PUT    /agents/{id}/drafts/{draft_id}       Update draft
DELETE /agents/{id}/drafts/{draft_id}       Delete draft
POST   /agents/{id}/drafts/{draft_id}/deploy  Deploy draft
GET    /agents/{id}/runs                    List runs
POST   /agents/{id}/runs                    Create run
GET    /agents/{id}/runs/{run_id}           Get run
PUT    /agents/{id}/runs/{run_id}           Update run
GET    /agents/{id}/statistics              Run statistics
GET    /agents/{id}/test-cases              List test cases
POST   /agents/{id}/test-cases              Create test case
DELETE /agents/{id}/test-cases/{case_id}    Delete test case

GET    /triggers                            List all triggers
GET    /triggers/{id}                       Get trigger
GET    /agents/{id}/triggers                List agent triggers
PUT    /agents/{id}/triggers                Set triggers
DELETE /agents/{id}/triggers                Delete triggers
POST   /agents/{id}/triggers/enable         Enable triggers
POST   /agents/{id}/triggers/disable        Disable triggers

GET    /admin/settings/                     Get all settings
GET    /admin/settings/{key}                Get setting
POST   /admin/settings/{key}                Update setting
PUT    /admin/settings/                     Bulk update
DELETE /admin/settings/{key}                Delete setting
GET    /admin/settings/health/check         Settings health
```

### agent_system (7 endpoints)

```
POST   /executions/run                      Start execution
GET    /executions/{id}                     Get status/results
POST   /executions/{id}/cancel              Cancel execution

POST   /inference/chat                      Start inference
GET    /inference/{id}                      Get status
POST   /inference/{id}/cancel               Cancel inference
WS     /inference/{id}/stream               Token streaming

GET    /admin/health                        Health check
```
