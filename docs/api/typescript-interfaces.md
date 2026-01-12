# TypeScript Interfaces

Complete TypeScript type definitions for all API request/response types.

---

## Enums

```typescript
// Hub enums
enum TaskType {
  TEXT_GENERATION = 'text-generation',
  TEXT_CLASSIFICATION = 'text-classification',
  QUESTION_ANSWERING = 'question-answering',
  SUMMARIZATION = 'summarization',
  TRANSLATION = 'translation'
}

enum LicenseType {
  APACHE_2_0 = 'apache-2.0',
  MIT = 'mit',
  GPL_3_0 = 'gpl-3.0',
  BSD = 'bsd',
  OTHER = 'other'
}

enum SortType {
  LIKES = 'likes',
  DOWNLOADS = 'downloads',
  TIME = 'time',
  UPDATE = 'update'
}

// Download enums
enum DownloadState {
  PENDING = 'pending',
  DOWNLOADING = 'downloading',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

enum ImportAction {
  COPY = 'copy',
  MOVE = 'move'
}

// Trigger enums
enum TriggerStatus {
  ENABLED = 'ENABLED',
  DISABLED = 'DISABLED',
  FAILED = 'FAILED'
}

// Execution enums
enum ExecutionStatus {
  PENDING = 'PENDING',
  RUNNING = 'RUNNING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  CANCELED = 'CANCELED',
  CANCEL_REQUESTED = 'CANCEL_REQUESTED'
}
```

---

## Hub Types

```typescript
interface SearchFilters {
  task?: TaskType;
  license?: LicenseType;
  min_downloads?: number;
  min_likes?: number;
  tags?: string[];
}

interface ModelInfoShort {
  repo_id: string;
  model_name: string;
  author: string;
  task?: TaskType;
  license?: LicenseType;
  downloads: number;
  likes: number;
  last_modified?: string;
  tags: string[];
}

interface ModelInfoDetailed extends ModelInfoShort {
  description?: string;
  readme_content?: string;
  model_card?: Record<string, any>;
  file_count: number;
  total_size_bytes?: number;
}

interface GGUFProvider {
  repo_id: string;
  provider_name: string;
  model_variants: string[];
  is_recommended: boolean;
  total_downloads: number;
  last_updated?: string;
}
```

---

## Download Types

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
  status: DownloadState;
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

---

## Local Models Types

```typescript
interface ImportRequest {
  file_path: string;
  action?: ImportAction;
}

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

## Agent Types

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

interface AgentCreatedResponse {
  agent_id: string;
  status: string;
}

interface StatusResponse {
  status: string;
}
```

---

## Version & Draft Types

```typescript
interface VersionItem {
  id: string;
  name: string;
  version?: number;
  base_version?: number;
  updated_at: string;
  is_active?: boolean;
  type: 'live' | 'draft';
}

interface VersionsResponse {
  versions: VersionItem[];
}

interface DraftCreate {
  name: string;
  source: string; // 'live' or draft UUID
}

interface DraftResponse {
  draft_id: string;
  name: string;
  base_version: number;
  updated_at: string;
  type: string;
}

interface DraftContentResponse {
  updated_at: string;
  graph: AgentGraph;
}

interface DraftUpdate {
  name?: string;
  expected_updated_at?: string;
  graph: AgentGraph;
}

interface AgentGraph {
  nodes: AgentNode[];
  edges: AgentEdge[];
  triggers: TriggerConfig[];
  permissions: Record<string, any>;
}

interface AgentNode {
  id: string;
  type: string;
  data: Record<string, any>;
}

interface AgentEdge {
  source: string;
  target: string;
}

interface DeployResponse {
  status: 'deployed' | 'deployed_inactive';
  new_version: number;
}
```

---

## Agent Run Types

```typescript
interface AgentRunCreate {
  trigger_type: string;
  status?: string;
}

interface AgentRunUpdate {
  status: string;
  error_message?: string;
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
```

---

## Test Case Types

```typescript
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

---

## Trigger Types

```typescript
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

## Settings Types

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

## Execution Types (agent_system)

```typescript
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

interface CancelResponse {
  status: string;
  execution_id?: string;
  task_id?: string;
}
```

---

## Inference Types (agent_system)

```typescript
interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

interface InferenceChatRequest {
  model_id: string;
  messages: ChatMessage[];
  parameters?: Record<string, any>;
}

interface InferenceChatResponse {
  task_id: string;
  status: string;
}

interface InferenceStatusResponse {
  task_id: string;
  model_id: string;
  status: ExecutionStatus;
  prompt: ChatMessage[];
  parameters: Record<string, any>;
  result?: Record<string, any>;
  tokens_per_second?: number;
  created_at: string;
  completed_at?: string;
}

// WebSocket Events
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

---

## Error Types

```typescript
interface ErrorResponse {
  error_code: string;
  message: string;
  details?: Record<string, any>;
  timestamp?: string;
}
```

---

## Health Types

```typescript
interface HealthResponse {
  status: string;
  timestamp?: string;
  version?: string;
}

interface AgentSystemHealthResponse {
  status: string;
  sqlite_version: string;
  uptime_sec: number;
}

interface SettingsHealthResponse {
  status: string;
  settings_count: number;
  message: string;
}
```
