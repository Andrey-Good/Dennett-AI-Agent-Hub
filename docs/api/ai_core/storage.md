# Storage API

Base URL: `http://127.0.0.1:8000`

Endpoints for storage management and file import.

---

## POST `/local/import`

Import a local GGUF file into Dennett library.

### Request Body

```json
{
  "file_path": "C:\\Downloads\\my-model.gguf",
  "action": "copy"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file_path` | string | Yes | Absolute path to GGUF file |
| `action` | enum | No | `copy` (default) or `move` |

### Action Values

| Action | Description |
|--------|-------------|
| `copy` | Copy file to Dennett storage (keeps original) |
| `move` | Move file to Dennett storage (removes original) |

### Example Request

```javascript
const model = await fetch('/local/import', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    file_path: 'C:\\Downloads\\mistral-7b.Q4_K_M.gguf',
    action: 'copy'
  })
}).then(r => r.json());
```

### Response (201 Created)

**Type:** `LocalModel`

```json
{
  "model_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_repo_id": null,
  "display_name": "mistral-7b.Q4_K_M.gguf",
  "file_path": "C:\\Users\\...\\Dennett\\models\\mistral-7b.Q4_K_M.gguf",
  "file_size_bytes": 4100000000,
  "file_hash": "abc123...",
  "imported_at": "2024-01-12T10:30:00Z",
  "last_accessed": null,
  "metadata": {},
  "is_downloaded": false
}
```

### Errors

| Code | Status | Description |
|------|--------|-------------|
| `FILE_NOT_FOUND` | 404 | Source file not found |
| `INVALID_FILE` | 400 | Invalid file format (not GGUF) |

---

## GET `/local/storage/stats`

Get storage usage statistics.

### Example Request

```javascript
const stats = await fetch('/local/storage/stats').then(r => r.json());
```

### Response

```json
{
  "total_size_bytes": 50000000000,
  "total_count": 5,
  "available_bytes": 100000000000,
  "usage_percent": 33.3
}
```

| Field | Type | Description |
|-------|------|-------------|
| `total_size_bytes` | number | Total size of all stored models |
| `total_count` | number | Number of models stored |
| `available_bytes` | number | Available disk space |
| `usage_percent` | number | Percentage of disk used by models |

---

## POST `/local/storage/cleanup`

Clean up orphaned files and old download records.

### Example Request

```javascript
const result = await fetch('/local/storage/cleanup', { method: 'POST' }).then(r => r.json());
```

### Response

```json
{
  "message": "Storage cleanup completed",
  "removed_files": ["orphan1.gguf", "orphan2.gguf"],
  "removed_count": 2
}
```

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Status message |
| `removed_files` | string[] | List of removed file names |
| `removed_count` | number | Number of files removed |

---

## Types

```typescript
interface ImportRequest {
  file_path: string;
  action?: 'copy' | 'move';
}

interface StorageStats {
  total_size_bytes: number;
  total_count: number;
  available_bytes: number;
  usage_percent: number;
}

interface CleanupResponse {
  message: string;
  removed_files: string[];
  removed_count: number;
}
```

---

## Usage Examples

### Display Storage Stats

```typescript
async function displayStorageInfo() {
  const stats = await fetch('/local/storage/stats').then(r => r.json());

  const totalGB = (stats.total_size_bytes / 1e9).toFixed(2);
  const availableGB = (stats.available_bytes / 1e9).toFixed(2);

  console.log(`Models: ${stats.total_count}`);
  console.log(`Used: ${totalGB} GB (${stats.usage_percent.toFixed(1)}%)`);
  console.log(`Available: ${availableGB} GB`);
}
```

### Import with Progress Feedback

```typescript
async function importModel(filePath: string, action: 'copy' | 'move' = 'copy') {
  try {
    const response = await fetch('/local/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: filePath, action })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message);
    }

    const model = await response.json();
    console.log(`Imported: ${model.display_name}`);
    return model;

  } catch (error) {
    console.error('Import failed:', error);
    throw error;
  }
}
```
