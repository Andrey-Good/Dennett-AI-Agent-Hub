# HuggingFace Hub API

Base URL: `http://127.0.0.1:8000`

Endpoints for searching and discovering models on HuggingFace Hub.

---

## GET `/hub/search`

Search for models on HuggingFace Hub.

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `limit` | integer | No | 20 | Results per page (1-100) |
| `offset` | integer | No | 0 | Skip N results |
| `sort` | enum | No | "likes" | Sort by: `likes`, `downloads`, `time`, `update` |
| `filters_json` | string | No | - | URL-encoded JSON filters |

### Example Request

```javascript
// Simple search
fetch('/hub/search?query=llama&limit=10')

// With sorting
fetch('/hub/search?query=llama&sort=downloads&limit=20')

// With filters
const filters = { task: 'text-generation', min_downloads: 1000 };
fetch(`/hub/search?query=llama&filters_json=${encodeURIComponent(JSON.stringify(filters))}`)
```

### Response

**Type:** `ModelInfoShort[]`

```json
[
  {
    "repo_id": "meta-llama/Llama-2-7b",
    "model_name": "Llama-2-7b",
    "author": "meta-llama",
    "task": "text-generation",
    "license": "apache-2.0",
    "downloads": 1500000,
    "likes": 5000,
    "last_modified": "2024-01-10T12:00:00Z",
    "tags": ["llm", "text-generation", "llama"]
  }
]
```

### Errors

| Code | Status | Description |
|------|--------|-------------|
| `INVALID_FILTERS` | 400 | Invalid filters JSON format |

---

## GET `/hub/model/{author}/{model_name}`

Get detailed information about a specific model.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `author` | string | Model author/organization |
| `model_name` | string | Model name |

### Example Request

```javascript
fetch('/hub/model/meta-llama/Llama-2-7b')
```

### Response

**Type:** `ModelInfoDetailed`

```json
{
  "repo_id": "meta-llama/Llama-2-7b",
  "model_name": "Llama-2-7b",
  "author": "meta-llama",
  "task": "text-generation",
  "license": "apache-2.0",
  "downloads": 1500000,
  "likes": 5000,
  "last_modified": "2024-01-10T12:00:00Z",
  "tags": ["llm", "text-generation"],
  "description": "Model description...",
  "readme_content": "# Model Card\n...",
  "model_card": {
    "language": ["en"],
    "pipeline_tag": "text-generation"
  },
  "file_count": 15,
  "total_size_bytes": 14000000000
}
```

---

## GET `/hub/model/{author}/{model_name}/gguf-providers`

Find GGUF format providers for a model.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `author` | string | Model author/organization |
| `model_name` | string | Model name |

### Example Request

```javascript
fetch('/hub/model/meta-llama/Llama-2-7b/gguf-providers')
```

### Response

**Type:** `GGUFProvider[]`

```json
[
  {
    "repo_id": "TheBloke/Llama-2-7B-GGUF",
    "provider_name": "TheBloke",
    "model_variants": ["Q4_K_M", "Q5_K_M", "Q8_0"],
    "is_recommended": true,
    "total_downloads": 500000,
    "last_updated": "2024-01-08T10:00:00Z"
  },
  {
    "repo_id": "other-provider/Llama-2-7B-GGUF",
    "provider_name": "other-provider",
    "model_variants": ["Q4_0", "Q5_0"],
    "is_recommended": false,
    "total_downloads": 10000,
    "last_updated": "2024-01-05T10:00:00Z"
  }
]
```

---

## Types

### SearchFilters

```typescript
interface SearchFilters {
  task?: 'text-generation' | 'text-classification' | 'question-answering' | 'summarization' | 'translation';
  license?: 'apache-2.0' | 'mit' | 'gpl-3.0' | 'bsd' | 'other';
  min_downloads?: number;
  min_likes?: number;
  tags?: string[];
}
```

### ModelInfoShort

```typescript
interface ModelInfoShort {
  repo_id: string;
  model_name: string;
  author: string;
  task?: string;
  license?: string;
  downloads: number;
  likes: number;
  last_modified?: string;
  tags: string[];
}
```

### ModelInfoDetailed

```typescript
interface ModelInfoDetailed extends ModelInfoShort {
  description?: string;
  readme_content?: string;
  model_card?: Record<string, any>;
  file_count: number;
  total_size_bytes?: number;
}
```

### GGUFProvider

```typescript
interface GGUFProvider {
  repo_id: string;
  provider_name: string;
  model_variants: string[];
  is_recommended: boolean;
  total_downloads: number;
  last_updated?: string;
}
```
