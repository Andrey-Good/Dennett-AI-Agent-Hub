# Local Models API

Base URL: `http://127.0.0.1:8000`

Endpoints for managing locally stored models.

---

## GET `/local/models`

List all locally stored models.

### Example Request

```javascript
const models = await fetch('/local/models').then(r => r.json());
```

### Response

**Type:** `LocalModel[]`

```json
[
  {
    "model_id": "550e8400-e29b-41d4-a716-446655440000",
    "original_repo_id": "TheBloke/Llama-2-7B-GGUF",
    "display_name": "llama-2-7b.Q4_K_M.gguf",
    "file_path": "C:\\Users\\...\\models\\llama-2-7b.Q4_K_M.gguf",
    "file_size_bytes": 4400000000,
    "file_hash": "abc123def456...",
    "imported_at": "2024-01-12T10:30:00Z",
    "last_accessed": "2024-01-12T12:00:00Z",
    "metadata": {},
    "is_downloaded": true
  }
]
```

---

## GET `/local/models/{model_id}`

Get details of a specific local model.

**Note:** This endpoint updates the `last_accessed` timestamp.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_id` | string | UUID of the model |

### Example Request

```javascript
const model = await fetch(`/local/models/${modelId}`).then(r => r.json());
```

### Response

**Type:** `LocalModel`

```json
{
  "model_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_repo_id": "TheBloke/Llama-2-7B-GGUF",
  "display_name": "llama-2-7b.Q4_K_M.gguf",
  "file_path": "C:\\Users\\...\\models\\llama-2-7b.Q4_K_M.gguf",
  "file_size_bytes": 4400000000,
  "file_hash": "abc123def456...",
  "imported_at": "2024-01-12T10:30:00Z",
  "last_accessed": "2024-01-12T14:30:00Z",
  "metadata": {},
  "is_downloaded": true
}
```

### Errors

| Code | Status | Description |
|------|--------|-------------|
| `MODEL_NOT_FOUND` | 404 | Model not found |

---

## DELETE `/local/models/{model_id}`

Delete a local model file and its metadata.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `model_id` | string | UUID of the model |

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `force` | boolean | false | Force deletion even if file appears in use |

### Example Request

```javascript
// Normal delete
await fetch(`/local/models/${modelId}`, { method: 'DELETE' });

// Force delete
await fetch(`/local/models/${modelId}?force=true`, { method: 'DELETE' });
```

### Response (204)

No content on success.

### Errors

| Code | Status | Description |
|------|--------|-------------|
| `MODEL_NOT_FOUND` | 404 | Model not found |
| `FILE_IN_USE` | 409 | File is in use (use `force=true` to override) |

---

## Types

```typescript
interface LocalModel {
  model_id: string;
  original_repo_id?: string;
  display_name: string;
  file_path: string;
  file_size_bytes: number;
  file_hash?: string;
  imported_at: string;
  last_accessed?: string;
  metadata: Record<string, any>;
  is_downloaded: boolean;
}
```

---

## Usage Examples

### List and Display Models

```typescript
async function displayLocalModels() {
  const models: LocalModel[] = await fetch('/local/models').then(r => r.json());

  models.forEach(model => {
    const sizeGB = (model.file_size_bytes / 1e9).toFixed(2);
    console.log(`${model.display_name} (${sizeGB} GB)`);
  });
}
```

### Delete with Confirmation

```typescript
async function deleteModel(modelId: string, force: boolean = false) {
  const url = force
    ? `/local/models/${modelId}?force=true`
    : `/local/models/${modelId}`;

  const response = await fetch(url, { method: 'DELETE' });

  if (response.status === 409) {
    const error = await response.json();
    if (confirm(`${error.message}\n\nForce delete?`)) {
      return deleteModel(modelId, true);
    }
  }

  if (!response.ok) {
    throw new Error('Failed to delete model');
  }
}
```
