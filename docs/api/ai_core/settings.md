# Settings API

Base URL: `http://127.0.0.1:8000`

Endpoints for managing application settings.

---

## GET `/admin/settings/`

Get all application settings.

**Response:**

```json
{
  "settings": {
    "theme": "dark",
    "language": "en",
    "api_key": "sk-..."
  },
  "count": 3
}
```

---

## GET `/admin/settings/{key}`

Get a specific setting by key.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | string | Setting key to retrieve |

**Response:**

```json
{
  "key": "theme",
  "value": "dark"
}
```

**Errors:**
- `404`: Setting not found

---

## POST `/admin/settings/{key}`

Update a single setting.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | string | Setting key to update |

**Request Body:**

```json
{
  "value": "light"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Setting 'theme' updated successfully",
  "key": "theme"
}
```

---

## PUT `/admin/settings/`

Update multiple settings at once.

**Request Body:**

```json
{
  "settings": {
    "theme": "dark",
    "language": "fr",
    "notifications": "enabled"
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "3 settings updated successfully"
}
```

---

## DELETE `/admin/settings/{key}`

Delete a setting by key.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | string | Setting key to delete |

**Response:**

```json
{
  "success": true,
  "message": "Setting 'theme' deleted successfully",
  "key": "theme"
}
```

**Errors:**
- `404`: Setting not found

---

## GET `/admin/settings/health/check`

Health check for settings service.

**Response:**

```json
{
  "status": "healthy",
  "settings_count": 10,
  "message": "Settings service is operational"
}
```

---

## Types

```typescript
interface SettingResponse {
  key: string;
  value: string;
}

interface SettingsResponse {
  settings: Record<string, string>;
  count: number;
}

interface UpdateSettingRequest {
  value: string;
}

interface UpdateSettingsRequest {
  settings: Record<string, string>;
}

interface SettingUpdateResponse {
  success: boolean;
  message: string;
  key?: string;
}
```

---

## Usage Examples

### Settings Manager Class

```typescript
class SettingsManager {
  private baseUrl = 'http://127.0.0.1:8000/admin/settings';

  async getAll(): Promise<Record<string, string>> {
    const response = await fetch(`${this.baseUrl}/`);
    const data = await response.json();
    return data.settings;
  }

  async get(key: string): Promise<string | null> {
    const response = await fetch(`${this.baseUrl}/${key}`);
    if (response.status === 404) return null;
    const data = await response.json();
    return data.value;
  }

  async set(key: string, value: string): Promise<void> {
    await fetch(`${this.baseUrl}/${key}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value })
    });
  }

  async setMany(settings: Record<string, string>): Promise<void> {
    await fetch(`${this.baseUrl}/`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ settings })
    });
  }

  async delete(key: string): Promise<boolean> {
    const response = await fetch(`${this.baseUrl}/${key}`, {
      method: 'DELETE'
    });
    return response.ok;
  }
}

// Usage
const settings = new SettingsManager();

// Get all settings
const all = await settings.getAll();

// Get single setting
const theme = await settings.get('theme');

// Update single setting
await settings.set('theme', 'dark');

// Update multiple settings
await settings.setMany({
  theme: 'dark',
  language: 'en',
  notifications: 'enabled'
});

// Delete setting
await settings.delete('old_setting');
```
