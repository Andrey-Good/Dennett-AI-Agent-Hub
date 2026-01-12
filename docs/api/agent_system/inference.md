# Inference API

Base URL: `http://127.0.0.1:8001`

Endpoints for model inference with real-time token streaming.

---

## POST `/inference/chat`

Start an inference task.

### Request Body

```json
{
  "model_id": "llama-2-7b",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 500
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model_id` | string | Yes | ID of the model to use |
| `messages` | array | Yes | Chat messages array |
| `parameters` | object | No | Generation parameters |

### Message Format

```typescript
interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}
```

### Common Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `temperature` | float | 0.7 | Sampling temperature (0-2) |
| `max_tokens` | int | 500 | Maximum tokens to generate |
| `top_p` | float | 1.0 | Nucleus sampling parameter |
| `top_k` | int | 50 | Top-k sampling parameter |

### Response

```json
{
  "task_id": "task-uuid",
  "status": "QUEUED"
}
```

---

## GET `/inference/{task_id}`

Get inference status and result.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `task_id` | string | UUID of the inference task |

### Response

```json
{
  "task_id": "task-uuid",
  "model_id": "llama-2-7b",
  "status": "COMPLETED",
  "prompt": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 500
  },
  "result": {
    "content": "I'm doing well, thank you for asking!",
    "finish_reason": "stop"
  },
  "tokens_per_second": 45.5,
  "created_at": "2024-01-12T10:00:00Z",
  "completed_at": "2024-01-12T10:00:15Z"
}
```

---

## POST `/inference/{task_id}/cancel`

Cancel an inference task.

### Response

```json
{
  "status": "cancel_requested",
  "task_id": "task-uuid"
}
```

---

## WebSocket `/inference/{task_id}/stream`

Stream inference tokens in real-time.

### Connection

```javascript
const ws = new WebSocket(`ws://127.0.0.1:8001/inference/${taskId}/stream`);
```

### Event Types

| Type | Data | Description |
|------|------|-------------|
| `TOKEN` | `{text: "..."}` | New token generated |
| `DONE` | `{result: {...}, tokens_per_second: N}` | Inference completed |
| `ERROR` | `{message: "...", trace: "..."}` | Error occurred |
| `CANCELED` | - | Inference was canceled |
| `PING` | - | Keep-alive (every 30s) |

### Event Data Structures

```typescript
interface TokenEvent {
  type: 'TOKEN';
  data: { text: string };
}

interface DoneEvent {
  type: 'DONE';
  data: {
    result: Record<string, any>;
    tokens_per_second: number;
  };
}

interface ErrorEvent {
  type: 'ERROR';
  data: {
    message: string;
    trace?: string;
  };
}

interface CanceledEvent {
  type: 'CANCELED';
}

interface PingEvent {
  type: 'PING';
}

type InferenceStreamEvent =
  | TokenEvent
  | DoneEvent
  | ErrorEvent
  | CanceledEvent
  | PingEvent;
```

### Basic Example

```javascript
const ws = new WebSocket(`ws://127.0.0.1:8001/inference/${taskId}/stream`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case 'TOKEN':
      // Append token to output
      outputDiv.textContent += data.data.text;
      break;

    case 'DONE':
      console.log('Complete!');
      console.log('Speed:', data.data.tokens_per_second, 'tok/s');
      ws.close();
      break;

    case 'ERROR':
      console.error('Error:', data.data.message);
      ws.close();
      break;

    case 'CANCELED':
      console.log('Canceled');
      ws.close();
      break;

    case 'PING':
      // Keep-alive, ignore
      break;
  }
};
```

---

## Types

```typescript
interface InferenceChatRequest {
  model_id: string;
  messages: ChatMessage[];
  parameters?: Record<string, any>;
}

interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

interface InferenceChatResponse {
  task_id: string;
  status: string;
}

interface InferenceStatusResponse {
  task_id: string;
  model_id: string;
  status: string;
  prompt: ChatMessage[];
  parameters: Record<string, any>;
  result?: Record<string, any>;
  tokens_per_second?: number;
  created_at: string;
  completed_at?: string;
}
```

---

## Complete Streaming Example

```typescript
class InferenceClient {
  private baseUrl = 'http://127.0.0.1:8001';
  private wsUrl = 'ws://127.0.0.1:8001';

  async chat(
    modelId: string,
    messages: ChatMessage[],
    options: {
      onToken?: (text: string) => void;
      onComplete?: (result: any, tokensPerSecond: number) => void;
      onError?: (message: string) => void;
      parameters?: Record<string, any>;
    } = {}
  ): Promise<string> {
    // Start inference task
    const response = await fetch(`${this.baseUrl}/inference/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model_id: modelId,
        messages,
        parameters: options.parameters
      })
    });

    const { task_id } = await response.json();

    // Connect to WebSocket for streaming
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(`${this.wsUrl}/inference/${task_id}/stream`);
      let fullText = '';

      ws.onmessage = (event) => {
        const data: InferenceStreamEvent = JSON.parse(event.data);

        switch (data.type) {
          case 'TOKEN':
            fullText += data.data.text;
            options.onToken?.(data.data.text);
            break;

          case 'DONE':
            options.onComplete?.(data.data.result, data.data.tokens_per_second);
            ws.close();
            resolve(fullText);
            break;

          case 'ERROR':
            options.onError?.(data.data.message);
            ws.close();
            reject(new Error(data.data.message));
            break;

          case 'CANCELED':
            ws.close();
            reject(new Error('Inference canceled'));
            break;
        }
      };

      ws.onerror = () => {
        reject(new Error('WebSocket connection error'));
      };
    });
  }

  async cancelInference(taskId: string): Promise<void> {
    await fetch(`${this.baseUrl}/inference/${taskId}/cancel`, {
      method: 'POST'
    });
  }
}

// Usage
const client = new InferenceClient();

const response = await client.chat(
  'llama-2-7b',
  [
    { role: 'system', content: 'You are a helpful assistant.' },
    { role: 'user', content: 'Tell me a joke.' }
  ],
  {
    onToken: (text) => {
      // Update UI with each token
      process.stdout.write(text);
    },
    onComplete: (result, speed) => {
      console.log(`\n\nGeneration speed: ${speed.toFixed(1)} tokens/sec`);
    },
    onError: (message) => {
      console.error('Error:', message);
    },
    parameters: {
      temperature: 0.8,
      max_tokens: 200
    }
  }
);

console.log('Full response:', response);
```

---

## React Hook Example

```typescript
import { useState, useCallback, useRef } from 'react';

interface UseInferenceOptions {
  modelId: string;
  onToken?: (text: string) => void;
}

function useInference({ modelId, onToken }: UseInferenceOptions) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState('');
  const wsRef = useRef<WebSocket | null>(null);
  const taskIdRef = useRef<string | null>(null);

  const send = useCallback(async (messages: ChatMessage[]) => {
    setIsLoading(true);
    setError(null);
    setResponse('');

    try {
      // Start task
      const res = await fetch('http://127.0.0.1:8001/inference/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: modelId, messages })
      });

      const { task_id } = await res.json();
      taskIdRef.current = task_id;

      // Connect WebSocket
      const ws = new WebSocket(`ws://127.0.0.1:8001/inference/${task_id}/stream`);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'TOKEN') {
          setResponse(prev => prev + data.data.text);
          onToken?.(data.data.text);
        }

        if (data.type === 'DONE') {
          setIsLoading(false);
        }

        if (data.type === 'ERROR') {
          setError(data.data.message);
          setIsLoading(false);
        }
      };

      ws.onerror = () => {
        setError('Connection error');
        setIsLoading(false);
      };

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setIsLoading(false);
    }
  }, [modelId, onToken]);

  const cancel = useCallback(async () => {
    if (taskIdRef.current) {
      await fetch(`http://127.0.0.1:8001/inference/${taskIdRef.current}/cancel`, {
        method: 'POST'
      });
    }
    wsRef.current?.close();
    setIsLoading(false);
  }, []);

  return { send, cancel, isLoading, error, response };
}

// Usage in component
function ChatComponent() {
  const { send, cancel, isLoading, error, response } = useInference({
    modelId: 'llama-2-7b'
  });

  const handleSubmit = (message: string) => {
    send([
      { role: 'system', content: 'You are a helpful assistant.' },
      { role: 'user', content: message }
    ]);
  };

  return (
    <div>
      {isLoading && <button onClick={cancel}>Cancel</button>}
      {error && <div className="error">{error}</div>}
      <div className="response">{response}</div>
    </div>
  );
}
```
