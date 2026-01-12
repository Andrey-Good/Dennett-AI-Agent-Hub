# Triggers API

Base URL: `http://127.0.0.1:8000`

Endpoints for managing trigger instances that automate agent execution.

---

## Global Trigger Endpoints

### GET `/triggers`

List all trigger instances across all agents.

**Query Parameters:**

| Parameter | Type | Default | Max |
|-----------|------|---------|-----|
| `limit` | integer | 100 | 1000 |
| `offset` | integer | 0 | - |

**Response:** `TriggerInstanceResponse[]`

```json
[
  {
    "trigger_instance_id": "trigger-uuid",
    "agent_id": "agent-uuid",
    "trigger_id": "cron",
    "status": "ENABLED",
    "config": {"schedule": "0 9 * * *"},
    "config_hash": "abc123...",
    "error_message": null,
    "error_at": null,
    "created_at": "2024-01-12T10:00:00Z",
    "updated_at": "2024-01-12T10:00:00Z"
  }
]
```

---

### GET `/triggers/{trigger_instance_id}`

Get trigger details by ID.

**Response:** `TriggerInstanceResponse`

**Errors:**
- `404`: Trigger not found

---

## Agent-Scoped Trigger Endpoints

### GET `/agents/{agent_id}/triggers`

List triggers for a specific agent.

**Response:** `TriggerInstanceResponse[]`

**Errors:**
- `404`: Agent not found or pending deletion

---

### PUT `/agents/{agent_id}/triggers`

Set triggers for an agent (idempotent replace operation).

This replaces all current triggers with the provided list:
- New triggers are created
- Missing triggers are deleted
- Existing triggers are updated if config changed

**Request Body:**

```json
{
  "triggers": [
    {
      "trigger_id": "cron",
      "status": "ENABLED",
      "config": {"schedule": "0 9 * * *"}
    },
    {
      "trigger_id": "webhook",
      "status": "ENABLED",
      "config": {"path": "/webhook/news"}
    }
  ]
}
```

**TriggerConfig Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `trigger_id` | string | Yes | Type of trigger (e.g., `cron`, `webhook`) |
| `status` | enum | No | `ENABLED` (default), `DISABLED` |
| `config` | object | No | Trigger-specific configuration |

**Response:**

```json
{
  "agent_id": "agent-uuid",
  "triggers": [...],
  "created": 1,
  "updated": 0,
  "deleted": 2
}
```

**Errors:**
- `400`: Invalid trigger configuration
- `404`: Agent not found or pending deletion

---

### DELETE `/agents/{agent_id}/triggers`

Delete all triggers for an agent.

**Response:**

```json
{
  "agent_id": "agent-uuid",
  "deleted": 3
}
```

---

### POST `/agents/{agent_id}/triggers/enable`

Enable all triggers for an agent.

**Note:** This also unfreezes `FAILED` triggers (resets error state).

**Response:**

```json
{
  "agent_id": "agent-uuid",
  "enabled": true,
  "affected": 3
}
```

---

### POST `/agents/{agent_id}/triggers/disable`

Disable all triggers for an agent.

**Response:**

```json
{
  "agent_id": "agent-uuid",
  "enabled": false,
  "affected": 3
}
```

---

## Trigger Status Values

| Status | Description |
|--------|-------------|
| `ENABLED` | Trigger is active and processing events |
| `DISABLED` | Trigger is paused (won't process events) |
| `FAILED` | Trigger crashed multiple times (frozen until enabled) |

---

## Common Trigger Types

| Type | Config Fields | Description |
|------|---------------|-------------|
| `cron` | `schedule` | Cron expression for scheduling |
| `webhook` | `path` | URL path for incoming webhooks |
| `file_system` | `watch_path`, `patterns` | Watch file system for changes |

---

## Types

```typescript
enum TriggerStatus {
  ENABLED = 'ENABLED',
  DISABLED = 'DISABLED',
  FAILED = 'FAILED'
}

interface TriggerConfig {
  trigger_id: string;
  status?: TriggerStatus;
  config?: Record<string, any>;
}

interface TriggerInstanceResponse {
  trigger_instance_id: string;
  agent_id: string;
  trigger_id: string;
  status: TriggerStatus;
  config: Record<string, any>;
  config_hash: string;
  error_message?: string;
  error_at?: string;
  created_at: string;
  updated_at: string;
}

interface SetAgentTriggersRequest {
  triggers: TriggerConfig[];
}

interface SetAgentTriggersResponse {
  agent_id: string;
  triggers: TriggerInstanceResponse[];
  created: number;
  updated: number;
  deleted: number;
}

interface DeleteAgentTriggersResponse {
  agent_id: string;
  deleted: number;
}

interface SetAgentTriggersEnabledResponse {
  agent_id: string;
  enabled: boolean;
  affected: number;
}
```

---

## Usage Examples

### Set Agent Triggers

```typescript
async function setAgentTriggers(agentId: string, triggers: TriggerConfig[]) {
  const response = await fetch(`/agents/${agentId}/triggers`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ triggers })
  });

  const result = await response.json();
  console.log(`Created: ${result.created}, Updated: ${result.updated}, Deleted: ${result.deleted}`);
  return result;
}

// Example: Set up cron and webhook triggers
await setAgentTriggers('agent-uuid', [
  {
    trigger_id: 'cron',
    status: 'ENABLED',
    config: { schedule: '0 9 * * *' }  // Every day at 9 AM
  },
  {
    trigger_id: 'webhook',
    status: 'ENABLED',
    config: { path: '/webhook/agent-trigger' }
  }
]);
```

### Toggle All Triggers

```typescript
async function toggleAgentTriggers(agentId: string, enabled: boolean) {
  const endpoint = enabled ? 'enable' : 'disable';
  const response = await fetch(`/agents/${agentId}/triggers/${endpoint}`, {
    method: 'POST'
  });
  return response.json();
}

// Enable all triggers
await toggleAgentTriggers('agent-uuid', true);

// Disable all triggers
await toggleAgentTriggers('agent-uuid', false);
```

### Check for Failed Triggers

```typescript
async function checkFailedTriggers(agentId: string) {
  const triggers = await fetch(`/agents/${agentId}/triggers`).then(r => r.json());

  const failed = triggers.filter(t => t.status === 'FAILED');

  if (failed.length > 0) {
    console.warn('Failed triggers detected:');
    failed.forEach(t => {
      console.warn(`- ${t.trigger_id}: ${t.error_message}`);
    });
  }

  return failed;
}
```
