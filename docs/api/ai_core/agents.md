# Agents API

Base URL: `http://127.0.0.1:8000`

Endpoints for agent management, versions, drafts, runs, and test cases.

---

## Agent CRUD

### GET `/agents`

List all agents with pagination.

**Query Parameters:**

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `limit` | integer | 100 | 1000 | Results per page |
| `offset` | integer | 0 | - | Skip N results |

**Response:** `AgentResponse[]`

```json
[
  {
    "id": "01234567-89ab-cdef-0123-456789abcdef",
    "name": "News Aggregator",
    "description": "Aggregates news from multiple sources",
    "tags": ["news", "aggregation"],
    "version": 3,
    "is_active": true,
    "updated_at": "2024-01-12T10:00:00Z"
  }
]
```

---

### POST `/agents`

Create a new agent.

**Request Body:**

```json
{
  "name": "News Aggregator",
  "description": "Aggregates news from multiple sources",
  "tags": ["news", "aggregation"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Agent name (1-255 chars) |
| `description` | string | No | Agent description |
| `tags` | string[] | No | Tags for categorization |

**Response (201):**

```json
{
  "agent_id": "01234567-89ab-cdef-0123-456789abcdef",
  "status": "created"
}
```

---

### GET `/agents/{agent_id}`

Get agent details by ID.

**Response:** `AgentResponse`

---

### PUT `/agents/{agent_id}`

Update agent properties (name, description, tags only).

**Request Body:**

```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "tags": ["updated", "tags"]
}
```

**Response:** `AgentResponse`

**Errors:**
- `404`: Agent not found
- `409`: Agent is marked for deletion

---

### DELETE `/agents/{agent_id}`

Soft delete an agent (marks for deletion).

**Response:**

```json
{
  "status": "marked_for_deletion"
}
```

---

## Agent Activation

### POST `/agents/{agent_id}/activate`

Activate agent (load triggers from live JSON).

**Response:**

```json
{
  "status": "active"
}
```

---

### POST `/agents/{agent_id}/deactivate`

Deactivate agent (unload triggers).

**Response:**

```json
{
  "status": "inactive"
}
```

---

## Versions & Drafts

### GET `/agents/{agent_id}/versions`

Get all versions (live + drafts).

**Response:**

```json
{
  "versions": [
    {
      "id": "agent-uuid",
      "name": "News Aggregator",
      "version": 3,
      "base_version": null,
      "updated_at": "2024-01-12T10:00:00.000Z",
      "is_active": true,
      "type": "live"
    },
    {
      "id": "draft-uuid",
      "name": "Experiment with RAG",
      "version": null,
      "base_version": 3,
      "updated_at": "2024-01-12T11:00:00.000Z",
      "is_active": null,
      "type": "draft"
    }
  ]
}
```

---

### POST `/agents/{agent_id}/drafts`

Create a new draft from live or another draft.

**Request Body:**

```json
{
  "name": "Experiment with RAG",
  "source": "live"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Draft name (1-255 chars) |
| `source` | string | `"live"` or draft UUID |

**Response (201):**

```json
{
  "draft_id": "draft-uuid",
  "name": "Experiment with RAG",
  "base_version": 3,
  "updated_at": "2024-01-12T11:00:00.000Z",
  "type": "draft"
}
```

---

### GET `/agents/{agent_id}/drafts/{draft_id}`

Get draft content for editing.

**Response:**

```json
{
  "updated_at": "2024-01-12T11:00:00.000Z",
  "graph": {
    "nodes": [
      {"id": "start", "type": "start", "data": {}},
      {"id": "end", "type": "end", "data": {}}
    ],
    "edges": [
      {"source": "start", "target": "end"}
    ],
    "triggers": [],
    "permissions": {}
  }
}
```

---

### PUT `/agents/{agent_id}/drafts/{draft_id}`

Update draft content (autosave with optimistic locking).

**Request Body:**

```json
{
  "name": "New Draft Name",
  "expected_updated_at": "2024-01-12T11:00:00.000Z",
  "graph": {
    "nodes": [...],
    "edges": [...],
    "triggers": [...],
    "permissions": {}
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | New draft name |
| `expected_updated_at` | string | No | For optimistic locking |
| `graph` | object | Yes | Graph JSON to save |

**Response:**

```json
{
  "status": "saved"
}
```

**Errors:**
- `404`: Draft not found
- `409`: Conflict - draft modified by another process

---

### DELETE `/agents/{agent_id}/drafts/{draft_id}`

Delete a draft.

**Response:**

```json
{
  "status": "deleted"
}
```

---

### POST `/agents/{agent_id}/drafts/{draft_id}/deploy`

Deploy a draft as the new live version.

**Response:**

```json
{
  "status": "deployed",
  "new_version": 4
}
```

| Status | Description |
|--------|-------------|
| `deployed` | Triggers successfully activated |
| `deployed_inactive` | Deployed but triggers failed to activate |

**Errors:**
- `409`: Draft based on outdated version (version conflict)
- `400`: Invalid triggers configuration

---

## Agent Runs

### GET `/agents/{agent_id}/runs`

List runs for an agent.

**Query Parameters:**

| Parameter | Type | Default | Max |
|-----------|------|---------|-----|
| `limit` | integer | 50 | 500 |
| `offset` | integer | 0 | - |

**Response:** `AgentRunResponse[]`

```json
[
  {
    "run_id": "run-uuid",
    "agent_id": "agent-uuid",
    "status": "completed",
    "priority": 70,
    "trigger_type": "manual",
    "start_time": "2024-01-12T10:00:00Z",
    "end_time": "2024-01-12T10:05:00Z",
    "error_message": null
  }
]
```

---

### POST `/agents/{agent_id}/runs`

Create a new run.

**Request Body:**

```json
{
  "trigger_type": "manual",
  "status": "pending"
}
```

**Trigger Types:** `manual`, `schedule`, `webhook`, `file_system`, `chat`, `chat_agent`

**Response (201):** `AgentRunResponse`

---

### GET `/agents/{agent_id}/runs/{run_id}`

Get run details.

**Response:** `AgentRunResponse`

---

### PUT `/agents/{agent_id}/runs/{run_id}`

Update run status.

**Request Body:**

```json
{
  "status": "completed",
  "error_message": null
}
```

**Response:** `AgentRunResponse`

---

### GET `/agents/{agent_id}/statistics`

Get agent run statistics.

**Response:**

```json
{
  "agent_id": "agent-uuid",
  "total_runs": 100,
  "completed": 85,
  "failed": 10,
  "pending": 5,
  "success_rate": 89.5,
  "avg_duration_seconds": 120.5
}
```

---

## Test Cases

### GET `/agents/{agent_id}/test-cases`

List test cases for an agent.

**Response:** `AgentTestCaseResponse[]`

```json
[
  {
    "case_id": "case-uuid",
    "agent_id": "agent-uuid",
    "node_id": "node_001",
    "name": "Test empty input",
    "initial_state": {
      "input": "",
      "expected_output": "Error message"
    }
  }
]
```

---

### POST `/agents/{agent_id}/test-cases`

Create a test case.

**Request Body:**

```json
{
  "node_id": "node_001",
  "name": "Test empty input",
  "initial_state": {
    "input": "",
    "expected_output": "Error message"
  }
}
```

**Response (201):** `AgentTestCaseResponse`

**Errors:**
- `404`: Agent not found
- `409`: Test case name already exists

---

### DELETE `/agents/{agent_id}/test-cases/{case_id}`

Delete a test case.

**Response (204):** No content

---

## Priority Levels

When creating runs, priority is assigned based on trigger type:

| Trigger Type | Priority | Description |
|--------------|----------|-------------|
| `chat` | 90 | Highest - interactive user chat |
| `manual` | 70 | User-initiated manual runs |
| `chat_agent` | 50 | Internal node-to-node calls |
| `schedule` | 30 | Scheduled triggers |
| `webhook` | 30 | Webhook triggers |
| `file_system` | 30 | File system triggers |

---

## Types

```typescript
interface AgentCreate {
  name: string;
  description?: string;
  tags?: string[];
}

interface AgentUpdate {
  name?: string;
  description?: string;
  tags?: string[];
}

interface AgentResponse {
  id: string;
  name: string;
  description?: string;
  tags: string[];
  version: number;
  is_active: boolean;
  updated_at: string;
}

interface VersionItem {
  id: string;
  name: string;
  version?: number;
  base_version?: number;
  updated_at: string;
  is_active?: boolean;
  type: 'live' | 'draft';
}

interface DraftCreate {
  name: string;
  source: string;
}

interface DraftUpdate {
  name?: string;
  expected_updated_at?: string;
  graph: AgentGraph;
}

interface AgentGraph {
  nodes: { id: string; type: string; data: Record<string, any> }[];
  edges: { source: string; target: string }[];
  triggers: TriggerConfig[];
  permissions: Record<string, any>;
}

interface AgentRunCreate {
  trigger_type: string;
  status?: string;
}

interface AgentRunResponse {
  run_id: string;
  agent_id: string;
  status: string;
  priority: number;
  trigger_type: string;
  start_time: string;
  end_time?: string;
  error_message?: string;
}

interface AgentStatistics {
  agent_id: string;
  total_runs: number;
  completed: number;
  failed: number;
  pending: number;
  success_rate: number;
  avg_duration_seconds?: number;
}

interface AgentTestCaseCreate {
  node_id: string;
  name: string;
  initial_state: Record<string, any>;
}

interface AgentTestCaseResponse {
  case_id: string;
  agent_id: string;
  node_id: string;
  name: string;
  initial_state: Record<string, any>;
}
```
