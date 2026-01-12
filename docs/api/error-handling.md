# Error Handling

Guide to handling API errors in frontend applications.

---

## Standard Error Response

All API errors follow this format:

```json
{
  "error_code": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": null,
  "timestamp": "2024-01-12T10:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `error_code` | string | Machine-readable error code |
| `message` | string | Human-readable error message |
| `details` | object | Additional error details (optional) |
| `timestamp` | string | Error timestamp (optional) |

---

## Common Error Codes

### General Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `NOT_FOUND` | 404 | Resource not found |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 502 | External service unavailable |

### Hub Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_FILTERS` | 400 | Invalid filters JSON format |

### Download Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `DOWNLOAD_NOT_FOUND` | 404 | Download not found |

### Model Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `MODEL_NOT_FOUND` | 404 | Model not found |
| `FILE_IN_USE` | 409 | File is in use (cannot delete) |
| `FILE_NOT_FOUND` | 404 | Source file not found |
| `INVALID_FILE` | 400 | Invalid file format |

### Agent Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AGENT_NOT_FOUND` | 404 | Agent not found |
| `DRAFT_NOT_FOUND` | 404 | Draft not found |
| `VERSION_CONFLICT` | 409 | Draft based on outdated version |
| `AGENT_PENDING_DELETION` | 409 | Agent is marked for deletion |

### Trigger Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `TRIGGER_NOT_FOUND` | 404 | Trigger not found |
| `INVALID_TRIGGER_CONFIG` | 400 | Invalid trigger configuration |

### Settings Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `SETTING_NOT_FOUND` | 404 | Setting not found |

---

## Error Handling Utility

```typescript
// Error types
interface ErrorResponse {
  error_code: string;
  message: string;
  details?: Record<string, any>;
  timestamp?: string;
}

class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public details?: Record<string, any>
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// Fetch wrapper with error handling
async function apiFetch<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let error: ErrorResponse;

    try {
      error = await response.json();
    } catch {
      throw new ApiError(
        'UNKNOWN_ERROR',
        `HTTP ${response.status}: ${response.statusText}`,
        response.status
      );
    }

    throw new ApiError(
      error.error_code || 'UNKNOWN_ERROR',
      error.message || 'Unknown error',
      response.status,
      error.details
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}
```

---

## Error Handling by Category

### Not Found (404)

```typescript
try {
  const model = await apiFetch<LocalModel>(`/local/models/${modelId}`);
} catch (error) {
  if (error instanceof ApiError && error.status === 404) {
    showNotification('Model not found');
    navigateTo('/models');
    return;
  }
  throw error;
}
```

### Conflict (409)

```typescript
try {
  await apiFetch(`/local/models/${modelId}`, { method: 'DELETE' });
} catch (error) {
  if (error instanceof ApiError && error.code === 'FILE_IN_USE') {
    const confirmed = confirm('File is in use. Force delete?');
    if (confirmed) {
      await apiFetch(`/local/models/${modelId}?force=true`, { method: 'DELETE' });
    }
    return;
  }
  throw error;
}
```

### Validation (400)

```typescript
try {
  await apiFetch('/hub/search', {
    method: 'GET',
    // ... with invalid filters
  });
} catch (error) {
  if (error instanceof ApiError && error.code === 'INVALID_FILTERS') {
    showError('Invalid search filters');
    return;
  }
  throw error;
}
```

### Draft Version Conflict (409)

```typescript
try {
  await apiFetch(`/agents/${agentId}/drafts/${draftId}/deploy`, {
    method: 'POST'
  });
} catch (error) {
  if (error instanceof ApiError && error.status === 409) {
    showError('Cannot deploy: the agent has been updated. Please refresh and try again.');
    refreshAgentVersions();
    return;
  }
  throw error;
}
```

---

## Global Error Handler

```typescript
// React example
function useApiErrorHandler() {
  const handleError = useCallback((error: unknown) => {
    if (error instanceof ApiError) {
      switch (error.status) {
        case 400:
          toast.error(`Invalid request: ${error.message}`);
          break;
        case 401:
          toast.error('Session expired. Please log in again.');
          logout();
          break;
        case 404:
          toast.error(`Not found: ${error.message}`);
          break;
        case 409:
          toast.warning(`Conflict: ${error.message}`);
          break;
        case 500:
        case 502:
        case 503:
          toast.error('Server error. Please try again later.');
          break;
        default:
          toast.error(error.message);
      }
    } else {
      toast.error('An unexpected error occurred');
      console.error(error);
    }
  }, []);

  return handleError;
}

// Usage
function MyComponent() {
  const handleError = useApiErrorHandler();

  const loadData = async () => {
    try {
      const data = await apiFetch('/api/data');
      setData(data);
    } catch (error) {
      handleError(error);
    }
  };
}
```

---

## Retry Logic

```typescript
async function fetchWithRetry<T>(
  url: string,
  options?: RequestInit,
  maxRetries: number = 3,
  delayMs: number = 1000
): Promise<T> {
  let lastError: Error | undefined;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await apiFetch<T>(url, options);
    } catch (error) {
      lastError = error as Error;

      // Don't retry client errors (4xx)
      if (error instanceof ApiError && error.status < 500) {
        throw error;
      }

      // Wait before retrying (exponential backoff)
      if (attempt < maxRetries - 1) {
        await new Promise(resolve =>
          setTimeout(resolve, delayMs * Math.pow(2, attempt))
        );
      }
    }
  }

  throw lastError;
}

// Usage
const data = await fetchWithRetry('/api/data', {}, 3, 1000);
```

---

## Error Boundary (React)

```typescript
import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ApiErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('API Error:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="error-container">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
          <button onClick={() => this.setState({ hasError: false })}>
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

// Usage
<ApiErrorBoundary>
  <MyComponent />
</ApiErrorBoundary>
```
