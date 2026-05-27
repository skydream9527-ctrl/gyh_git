export interface ApiEnvelope<T = unknown> {
  code: number;
  message: string;
  error_code?: string;
  /** 后端中间件给每个请求分配的 8 字符 ID。出错时贴给 admin 反查事件流。 */
  request_id?: string;
  data: T;
}

export interface PageData<T> {
  items: T[];
  total: number;
  page?: number;
  page_size?: number;
  unread?: number;
}

export interface UserPublic {
  id: string;
  email: string;
  name: string;
  auth_role: "user" | "admin" | "super_admin";
  avatar_url?: string | null;
  feishu_bound: boolean;
  team?: string | null;
  title?: string | null;
  /** 小米办公邮箱（@xiaomi.com / @mi.com）。用于 feishu_publish 自动加权限。 */
  xiaomi_email?: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginResponse {
  user: UserPublic;
  tokens: TokenPair;
}

/** Registration now goes through admin approval — the backend returns this
 * shape (no tokens) and the SPA must show a "wait for approval" screen. */
export interface RegisterResponse {
  status: "pending";
  user: UserPublic;
  message: string;
}

export interface AgentCard {
  id: string;
  name: string;
  paradigm: string;
  icon: string;
  color: string;
  description?: string;
  publish_status?: string;
}

export interface SkillCard {
  id: string;
  name: string;
  description: string;
  description_zh?: string | null;
  category: string;
  tool_entry: string;
  tool_schema?: Record<string, unknown>;
  builtin?: boolean;
  enabled?: boolean;
}

export interface TaskSummary {
  id: string;
  name: string;
  paradigm: string;
  agent_id?: string | null;
  owner_id: string;
  /** 后端 list_public_tasks 批量从 users_index 注入；个人任务列表不含此字段。 */
  owner_name?: string;
  status: string;
  visibility: string;
  file_count: number;
  last_message_preview?: string | null;
  updated_at?: string | null;
  created_at?: string | null;
  role?: "owner" | "collaborator";
}

/** 详情接口里的 `role` 是后端 derive_task_role 派生的细粒度角色（owner/editor/viewer/admin），
 *  与列表接口里 TaskSummary.role 的"owner|collaborator"粗粒度含义不同，故 Omit 后重新声明，
 *  避免类型冲突，也提醒维护者两处含义不一样。 */
export interface TaskDetail extends Omit<TaskSummary, "role"> {
  description?: string | null;
  initial_prompt?: string | null;
  skill_ids?: string[];
  collaborators?: Array<{ user_id: string; role: string; status: string }>;
  /** 当前调用者在该任务上的角色，由后端 derive_task_role 派生回传，前端直接用——
   *  前端再自己算一次 role 容易和后端漏档（曾出现 viewer 协作者拿到编辑态 UI 的 BUG）。 */
  role?: "owner" | "editor" | "viewer" | "admin" | null;
  workspace?: { current_conversation_id?: string; model?: string };
  agent_update_available?: boolean;
  imported_file_count?: number;
  snapshot?: {
    mode: "live" | "frozen";
    agent_source_version: string | null;
    frozen_at: string | null;
    frozen_by: string | null;
    last_manual_update_at: string | null;
    last_manual_update_by: string | null;
  };
}

export interface FileMeta {
  id: string;
  name: string;
  path: string;
  scope: "input" | "output" | "uploaded" | "public" | "imported";
  task_id?: string | null;
  file_type?: string | null;
  format?: string | null;
  size_bytes: number;
  is_pinned: boolean;
  created_at?: string | null;
  // Imported-file fields (source_type = kb_article | feishu_doc)
  source_type?: "kb_article" | "feishu_doc" | null;
  source_url?: string | null;
  source_ref?: {
    kb_id?: string;
    article_id?: string;
    url?: string;
    [k: string]: unknown;
  } | null;
  imported_at?: string | null;
  imported_by?: string | null;
  last_refreshed_at?: string | null;
  // Backend uses these alternate keys for imported files
  file_id?: string | null;
  filename?: string | null;
  size?: number | null;
  // Platform-generated read-only docs (guide / per-agent / per-skill)
  builtin?: boolean;
  builtin_kind?: "guide" | "agent" | "skill";
  owner_name?: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_by: string;
  created_by_name?: string;
  created_at: string;
  last_message_at: string;
  message_count: number;
  /** 当前 worker 内是否有正在跑的回合（后端 _inflight_turns）。
   * 前端用它给对话项加 ⏳ 角标，提示「切走后后台还在生成」。 */
  inflight?: boolean;
}

export interface JoinRequest {
  id: string;
  user_id: string;
  message: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  reviewed_at?: string | null;
  reviewed_by?: string | null;
  reject_reason?: string | null;
}

export interface AgentRefreshResult {
  changed: boolean;
  new_version?: string;
  diff_summary?: {
    cards_added: number;
    cards_removed: number;
    system_changed: boolean;
  };
}

export interface FileRefreshResult {
  changed: boolean;
  size: number;
  last_refreshed_at: string;
}

export interface NotificationItem {
  id: string;
  kind:
    | "experience"
    | "task-fail"
    | "collaboration"
    | "token-alert"
    | "system"
    | "public-task-pending";
  title: string;
  body: string;
  action_url?: string | null;
  is_read: boolean;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  tool_uses?: Array<{ id: string; name: string; input: Record<string, unknown> }>;
  agent_id?: string;
  user_id?: string;
  created_at: string;
}

export interface ToolCall {
  tool_call_id: string;
  tool_name: string;
  display_name?: string;
  arguments: Record<string, unknown>;
  status: "executing" | "done" | "error" | "timeout";
  result?: unknown;
  error?: { code: string; message: string };
}

export interface GlobalToggles {
  feishu_enabled: boolean;
  llm_enabled: boolean;
  voice_enabled?: boolean;
  enable_open_register: boolean;
  upload_max_size_mb: number;
  upload_max_size_hard_cap_mb: number;
}
