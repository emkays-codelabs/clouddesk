// Mirrors docs/design/06_API_CONTRACT.md. Change the contract, the backend schemas and this file together.

export type Role = "admin" | "agent" | "viewer";
export type TicketStatus =
  | "new"
  | "in_progress"
  | "waiting_on_customer"
  | "waiting_on_approval"
  | "escalated"
  | "resolved"
  | "closed";
export type Severity = "low" | "medium" | "high" | "critical";
export type Channel = "email" | "chat" | "web" | "api";
export type ApprovalStatus = "not_required" | "pending" | "approved" | "rejected";
export type WorkflowStatus =
  | "running"
  | "waiting_for_approval"
  | "completed"
  | "failed"
  | "escalated";

export type User = {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  avatar_url?: string | null;
};

export type LoginResponse = { access_token: string; token_type: "bearer"; user: User };

export type TicketSummary = {
  id: string;
  ticket_number: string;
  subject: string;
  status: TicketStatus;
  severity: Severity | null;
  category: string | null;
  customer_id: string;
  customer_name: string;
  channel: Channel;
  created_at: string;
  updated_at: string;
  escalation_required: boolean;
  approval_status: ApprovalStatus;
};

export type Ticket = TicketSummary & {
  body: string;
  assigned_to?: string | null;
  resolved_at?: string | null;
  tags: string[];
};

export type TicketMessage = {
  id: string;
  ticket_id: string;
  role: "customer" | "agent" | "system" | "ai";
  author_name: string;
  body: string;
  internal: boolean;
  created_at: string;
};

export type Customer = {
  id: string;
  name: string;
  email: string;
  company: string;
  plan_name: string;
  status: string;
  region?: string;
  created_at: string;
};

export type Subscription = {
  id: string;
  customer_id: string;
  plan: string;
  seats: number;
  status: string;
  mrr: number;
  storage_quota_gb: number;
  storage_used_gb: number;
  api_rate_limit: number;
};

export type Workspace = {
  id: string;
  name: string;
  member_count: number;
  storage_used_gb: number;
  integrations: string[];
  sso_enabled: boolean;
};

export type CustomerMemory = {
  id: string;
  memory_type: string;
  content: string;
  confidence?: number;
};

export type CustomerDetail = Customer & {
  subscription: Subscription | null;
  workspace: Workspace | null;
  tickets: TicketSummary[];
  memory: CustomerMemory[];
};

export type Evidence = {
  id: string;
  title: string;
  source: string;
  snippet: string;
  score: number;
  url?: string | null;
  article_id?: string | null;
};

export type PlannedAction = {
  tool: string;
  arguments: Record<string, unknown>;
  requires_approval: boolean;
  description: string;
};

export type ResolutionAction = {
  id: string;
  ticket_id: string;
  tool: string;
  arguments: Record<string, unknown>;
  status: "planned" | "pending_approval" | "approved" | "executed" | "rejected" | "failed";
  result: Record<string, unknown> | null;
  requires_approval: boolean;
};

export type Escalation = {
  id: string;
  ticket_id: string;
  ticket_number: string;
  reason: string;
  priority: string;
  status: "open" | "acknowledged" | "resolved";
  created_by: string;
  assigned_team: string;
  created_at: string;
};

export type WorkflowState = {
  workflow_id: string;
  ticket_id: string;
  status: WorkflowStatus;
  current_node: string | null;
  completed_nodes: string[];
  classification?: { category: string; intent: string; summary: string; confidence: number } | null;
  severity?: Severity | null;
  severity_reason?: string | null;
  retrieved_docs: Evidence[];
  diagnosis?: {
    problem: string;
    probable_causes: string[];
    troubleshooting_steps: string[];
    confidence: number;
  } | null;
  resolution_plan?: {
    summary: string;
    customer_response: string;
    internal_notes: string;
    actions: PlannedAction[];
  } | null;
  actions: ResolutionAction[];
  risk?: { level: "low" | "medium" | "high"; reasons: string[] } | null;
  escalation_required: boolean;
  escalation_reason?: string | null;
  approval_status: ApprovalStatus;
  approval_request_id?: string | null;
  final_response?: string | null;
  ticket_summary?: string | null;
  errors: string[];
  token_usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    estimated_cost_usd: number;
  };
};

export type TicketDetail = Ticket & {
  messages: TicketMessage[];
  customer: Customer;
  subscription: Subscription | null;
  history: TicketSummary[];
  workflow: WorkflowState | null;
  resolution_actions: ResolutionAction[];
  escalation: Escalation | null;
};

export type ApprovalRequest = {
  id: string;
  ticket_id: string;
  ticket_number: string;
  workflow_id: string;
  action: PlannedAction;
  risk_level: string;
  reason: string;
  requested_by: string;
  status: "pending" | "approved" | "rejected";
  decided_by?: string | null;
  decision_note?: string | null;
  created_at: string;
};

export type WorkflowEvent = {
  id: string;
  event_type: string;
  node: string | null;
  tool: string | null;
  message: string;
  duration_ms: number | null;
  created_at: string;
};

export type Page<T> = { items: T[]; total: number; page: number; page_size: number };

export type DashboardSummary = {
  open_tickets: number;
  resolved_today: number;
  pending_approvals: number;
  escalations_open: number;
  avg_resolution_minutes: number;
  by_severity: Record<string, number>;
  by_category: Record<string, number>;
  recent_tickets: TicketSummary[];
};

export type AuditLog = {
  id: string;
  actor: string;
  actor_type: string;
  action: string;
  resource_type: string;
  resource_id: string;
  request_id: string | null;
  created_at: string;
};

export type Article = { id: string; slug: string; title: string; category: string; summary: string };

export type AgentsOverview = {
  agents: { name: string; role: string; description: string; tools: string[]; runs: number }[];
  graph: { nodes: { id: string; label: string }[]; edges: { source: string; target: string; label?: string }[] };
  recent_runs: WorkflowState[];
  stats: {
    runs_total: number;
    runs_completed: number;
    runs_failed: number;
    avg_duration_ms: number;
    total_tokens: number;
    total_estimated_cost_usd: number;
  };
};

export type AppSettings = {
  demo_mode: boolean;
  environment: string;
  llm: { llm_provider: string; llm_model: string; api_key_configured: boolean };
  vector_store: string;
  database: string;
  approval_policy: { refunds_require_approval: boolean; max_refund_without_approval: number };
};
