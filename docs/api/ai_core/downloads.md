# Downloads API

Base URL: `http://127.0.0.1:8000`

Endpoints for managing model file downloads with real-time progress tracking.

---

## POST `/local/download`

Start downloading a model file.

### Request Body

```json
{
  "repo_id": "TheBloke/Llama-2-7B-GGUF",
  "filename": "llama-2-7b.Q4_K_M.gguf"
}
```

### Example Request

```javascript
const response = await fetch('/local/download', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    repo_id: 'TheBloke/Llama-2-7B-GGUF',
    filename: 'llama-2-7b.Q4_K_M.gguf'
  })
});

const { download_id } = await response.json();
```

### Response (202 Accepted)

```json
{
  "download_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Download started for TheBloke/Llama-2-7B-GGUF/llama-2-7b.Q4_K_M.gguf"
}
```

---

## GET `/local/download/status`

Subscribe to real-time download updates via Server-Sent Events (SSE).

### Headers

```
Accept: text/event-stream
```

### Example Usage

```javascript
const eventSource = new EventSource('/local/download/status');

eventSource.onmessage = (event) => {
  const status = JSON.parse(event.data);

  console.log(`Download ${status.download_id}: ${status.progress_percent.toFixed(1)}%`);

  if (status.status === 'completed') {
    console.log('Download complete:', status.local_file_path);
  }

  if (status.status === 'failed') {
    console.error('Download failed:', status.error_message);
  }
};

eventSource.onerror = (error) => {
  console.error('SSE connection error:', error);
  eventSource.close();
};

// Clean up when done
// eventSource.close();
```

### Event Data

**Type:** `DownloadStatus`

```json
{
  "download_id": "550e8400-e29b-41d4-a716-446655440000",
  "repo_id": "TheBloke/Llama-2-7B-GGUF",
  "filename": "llama-2-7b.Q4_K_M.gguf",
  "status": "downloading",
  "progress_percent": 45.5,
  "bytes_downloaded": 2000000000,
  "total_bytes": 4400000000,
  "download_speed_mbps": 25.5,
  "eta_seconds": 120,
  "error_message": null,
  "started_at": "2024-01-12T10:00:00Z",
  "completed_at": null,
  "local_file_path": null
}
```

### Status Values

| Status | Description |
|--------|-------------|
| `pending` | Download queued, not yet started |
| `downloading` | Download in progress |
| `completed` | Download finished successfully |
| `failed` | Download failed (check `error_message`) |
| `cancelled` | Download was cancelled |

---

## DELETE `/local/download/{download_id}`

Cancel an active download.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `download_id` | string | UUID of the download |

### Example Request

```javascript
await fetch(`/local/download/${downloadId}`, { method: 'DELETE' });
```

### Response (200)

```json
{
  "message": "Download cancelled successfully"
}
```

### Errors

| Code | Status | Description |
|------|--------|-------------|
| `DOWNLOAD_NOT_FOUND` | 404 | Download not found |

---

## SSE Integration Helper

```typescript
class DownloadProgressManager {
  private eventSource: EventSource | null = null;
  private listeners: Map<string, (status: DownloadStatus) => void> = new Map();

  connect(baseUrl: string = 'http://127.0.0.1:8000') {
    this.eventSource = new EventSource(`${baseUrl}/local/download/status`);

    this.eventSource.onmessage = (event) => {
      const status: DownloadStatus = JSON.parse(event.data);

      // Notify specific listener
      const listener = this.listeners.get(status.download_id);
      if (listener) {
        listener(status);
      }

      // Clean up completed downloads
      if (['completed', 'failed', 'cancelled'].includes(status.status)) {
        this.listeners.delete(status.download_id);
      }
    };

    this.eventSource.onerror = () => {
      // Reconnect after delay
      setTimeout(() => {
        this.disconnect();
        this.connect(baseUrl);
      }, 5000);
    };
  }

  subscribe(downloadId: string, callback: (status: DownloadStatus) => void) {
    this.listeners.set(downloadId, callback);
  }

  unsubscribe(downloadId: string) {
    this.listeners.delete(downloadId);
  }

  disconnect() {
    this.eventSource?.close();
    this.eventSource = null;
  }
}

// Usage
const manager = new DownloadProgressManager();
manager.connect();

// Start a download
const { download_id } = await startDownload(repoId, filename);

// Subscribe to progress
manager.subscribe(download_id, (status) => {
  updateProgressBar(status.progress_percent);

  if (status.status === 'completed') {
    showSuccess('Download complete!');
  }
});
```

---

## Types

```typescript
interface DownloadRequest {
  repo_id: string;
  filename: string;
}

interface DownloadResponse {
  download_id: string;
  message: string;
}

interface DownloadStatus {
  download_id: string;
  repo_id: string;
  filename: string;
  status: 'pending' | 'downloading' | 'completed' | 'failed' | 'cancelled';
  progress_percent: number;
  bytes_downloaded: number;
  total_bytes?: number;
  download_speed_mbps?: number;
  eta_seconds?: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  local_file_path?: string;
}
```
