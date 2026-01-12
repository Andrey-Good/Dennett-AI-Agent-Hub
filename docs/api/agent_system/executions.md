# Executions API

Base URL: `http://127.0.0.1:8001`

Endpoints for running agent executions.

---

## POST `/executions/run`

Start an agent execution.

### Request Body

```json
{
  "agent_id": "agent-uuid",
  "input": {
    "question": "What is the weather today?",
    "context": {}
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_id` | string | Yes | UUID of the agent to run |
| `input` | object | No | Input data for the agent |

### Example Request

```javascript
const response = await fetch('http://127.0.0.1:8001/executions/run', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    agent_id: 'agent-uuid',
    input: {
      question: 'What is the weather today?'
    }
  })
});

const { execution_id } = await response.json();
```

### Response

```json
{
  "execution_id": "exec-uuid",
  "status": "QUEUED"
}
```

---

## GET `/executions/{execution_id}`

Get execution status and results.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `execution_id` | string | UUID of the execution |

### Example Request

```javascript
const result = await fetch(`http://127.0.0.1:8001/executions/${executionId}`).then(r => r.json());
```

### Response

```json
{
  "execution_id": "exec-uuid",
  "agent_id": "agent-uuid",
  "status": "COMPLETED",
  "priority": 70,
  "payload": {
    "question": "What is the weather today?"
  },
  "final_result": {
    "answer": "Today is sunny with 25C",
    "confidence": 0.95
  },
  "error_log": null,
  "created_at": "2024-01-12T10:00:00Z",
  "started_at": "2024-01-12T10:00:01Z",
  "completed_at": "2024-01-12T10:00:30Z"
}
```

### Status Values

| Status | Description |
|--------|-------------|
| `PENDING` | Execution queued, waiting to start |
| `RUNNING` | Execution in progress |
| `COMPLETED` | Execution finished successfully |
| `FAILED` | Execution failed (check `error_log`) |
| `CANCELED` | Execution was canceled |
| `CANCEL_REQUESTED` | Cancel requested, stopping |

### Errors

- `404`: Execution not found

---

## POST `/executions/{execution_id}/cancel`

Cancel a running execution.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `execution_id` | string | UUID of the execution |

### Example Request

```javascript
await fetch(`http://127.0.0.1:8001/executions/${executionId}/cancel`, {
  method: 'POST'
});
```

### Response

```json
{
  "status": "cancel_requested",
  "execution_id": "exec-uuid"
}
```

### Errors

- `404`: Execution not found

---

## GET `/admin/health`

Health check endpoint.

### Response

```json
{
  "status": "ok",
  "sqlite_version": "3.39.0",
  "uptime_sec": 3600
}
```

---

## Types

```typescript
enum ExecutionStatus {
  PENDING = 'PENDING',
  RUNNING = 'RUNNING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  CANCELED = 'CANCELED',
  CANCEL_REQUESTED = 'CANCEL_REQUESTED'
}

interface ExecutionRunRequest {
  agent_id: string;
  input?: Record<string, any>;
}

interface ExecutionRunResponse {
  execution_id: string;
  status: string;
}

interface ExecutionStatusResponse {
  execution_id: string;
  agent_id: string;
  status: ExecutionStatus;
  priority: number;
  payload: Record<string, any>;
  final_result?: Record<string, any>;
  error_log?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}
```

---

## Usage Examples

### Run and Poll for Result

```typescript
async function runAgentAndWait(
  agentId: string,
  input: Record<string, any>,
  timeoutMs: number = 60000
): Promise<any> {
  // Start execution
  const startResponse = await fetch('http://127.0.0.1:8001/executions/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_id: agentId, input })
  });

  const { execution_id } = await startResponse.json();

  // Poll for completion
  const startTime = Date.now();
  while (Date.now() - startTime < timeoutMs) {
    const statusResponse = await fetch(
      `http://127.0.0.1:8001/executions/${execution_id}`
    );
    const status = await statusResponse.json();

    if (status.status === 'COMPLETED') {
      return status.final_result;
    }

    if (status.status === 'FAILED') {
      throw new Error(status.error_log || 'Execution failed');
    }

    if (status.status === 'CANCELED') {
      throw new Error('Execution was canceled');
    }

    // Wait before polling again
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  throw new Error('Execution timed out');
}

// Usage
try {
  const result = await runAgentAndWait('agent-uuid', {
    question: 'What is the weather?'
  });
  console.log('Result:', result);
} catch (error) {
  console.error('Execution failed:', error);
}
```

### Cancel on User Action

```typescript
class ExecutionManager {
  private activeExecutions: Map<string, AbortController> = new Map();

  async start(agentId: string, input: Record<string, any>): Promise<string> {
    const response = await fetch('http://127.0.0.1:8001/executions/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: agentId, input })
    });

    const { execution_id } = await response.json();
    this.activeExecutions.set(execution_id, new AbortController());
    return execution_id;
  }

  async cancel(executionId: string): Promise<void> {
    await fetch(`http://127.0.0.1:8001/executions/${executionId}/cancel`, {
      method: 'POST'
    });
    this.activeExecutions.delete(executionId);
  }

  async cancelAll(): Promise<void> {
    const cancelPromises = Array.from(this.activeExecutions.keys()).map(id =>
      this.cancel(id)
    );
    await Promise.all(cancelPromises);
  }
}
```
