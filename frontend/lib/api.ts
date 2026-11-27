// The only way the console talks to the backend (CLAUDE.md 11): a typed client with the bearer token
// in localStorage, a redirect to /login on 401 and a NetworkError (retried with a short backoff) when
// the server cannot be reached. The browser only ever holds the user's own token.
import type {
  AgentsOverview,
  AppSettings,
  ApprovalRequest,
  Article,
  AuditLog,
  Customer,
  CustomerDetail,
  DashboardSummary,
  Escalation,
  LoginResponse,
  Page,
  TicketDetail,
  TicketMessage,
  TicketSummary,
  User,
  WorkflowEvent,
  WorkflowState,
} from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const TOKEN_KEY = "clouddesk_token";
const PREFIX = "/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

export class NetworkError extends Error {
  constructor(message = "The server cannot be reached.") {
    super(message);
    this.name = "NetworkError";
  }
}

export function getToken(): string | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* storage can be blocked; the session then lasts until reload */
  }
}

export function clearToken(): void {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* nothing to clear */
  }
}

let onUnauthorized: () => void = () => {
  if (typeof window !== "undefined") window.location.assign("/login?reason=expired");
};

/** Replace what happens on a 401 (the default sends the browser to /login?reason=expired). */
export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

type Query = Record<string, string | number | boolean | null | undefined>;
type Options = { method?: string; body?: unknown; query?: Query; retries?: number; auth?: boolean };

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function url(path: string, query?: Query): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const qs = search.toString();
  return `${API_URL}${path}${qs ? `?${qs}` : ""}`;
}

export async function request<T>(path: string, options: Options = {}): Promise<T> {
  const { method = "GET", body, query, auth = true } = options;
  const retries = options.retries ?? (method === "GET" ? 2 : 0);
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const response = await fetch(url(path, query), {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      if (response.status === 401 && auth) {
        clearToken();
        onUnauthorized();
        throw new ApiError(401, "Your session has expired.");
      }
      if (!response.ok) {
        let detail = response.statusText;
        try {
          const data = await response.json();
          if (typeof data?.detail === "string") detail = data.detail;
        } catch {
          /* keep the status text */
        }
        throw new ApiError(response.status, detail);
      }
      return (response.status === 204 ? undefined : await response.json()) as T;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      lastError = error;
      if (attempt < retries) await sleep(250 * 2 ** attempt);
    }
  }
  throw new NetworkError(lastError instanceof Error ? lastError.message : undefined);
}

const p = (path: string) => `${PREFIX}${path}`;

export const api = {
  login: (email: string) =>
    request<LoginResponse>(p("/auth/demo-login"), { method: "POST", body: { email }, auth: false }),
  me: () => request<User>(p("/auth/me")),
  dashboard: () => request<DashboardSummary>(p("/dashboard/summary")),
  tickets: (query?: Query) => request<Page<TicketSummary>>(p("/tickets"), { query }),
  ticket: (id: string) => request<TicketDetail>(p(`/tickets/${id}`)),
  workflow: (id: string) => request<WorkflowState>(p(`/tickets/${id}/workflow`)),
  events: (id: string) => request<WorkflowEvent[]>(p(`/tickets/${id}/events`)),
  runWorkflow: (id: string) =>
    request<{ workflow_id: string; status: string }>(p(`/tickets/${id}/run`), { method: "POST" }),
  reply: (id: string, body: string, internal = false) =>
    request<TicketMessage>(p(`/tickets/${id}/reply`), { method: "POST", body: { body, internal } }),
  requestInfo: (id: string, questions: string[]) =>
    request<TicketMessage>(p(`/tickets/${id}/request-info`), { method: "POST", body: { questions } }),
  escalate: (id: string, reason: string, priority: "normal" | "urgent" = "normal") =>
    request<Escalation>(p(`/tickets/${id}/escalate`), { method: "POST", body: { reason, priority } }),
  approvals: (status?: string) => request<ApprovalRequest[]>(p("/approvals"), { query: { status } }),
  approve: (id: string, note?: string) =>
    request<{ approval: ApprovalRequest; workflow: WorkflowState | null }>(
      p(`/approvals/${id}/approve`),
      { method: "POST", body: { note } },
    ),
  reject: (id: string, note?: string) =>
    request<{ approval: ApprovalRequest; workflow: WorkflowState | null }>(
      p(`/approvals/${id}/reject`),
      { method: "POST", body: { note } },
    ),
  customers: (query?: Query) => request<Page<Customer>>(p("/customers"), { query }),
  customer: (id: string) => request<CustomerDetail>(p(`/customers/${id}`)),
  articles: (query?: Query) => request<Article[]>(p("/knowledge/articles"), { query }),
  searchKnowledge: (query: string) =>
    request<{ results: { id: string; title: string; snippet: string; score: number }[] }>(
      p("/knowledge/search"),
      { method: "POST", body: { query, top_k: 5 } },
    ),
  escalations: (status?: string) => request<Escalation[]>(p("/escalations"), { query: { status } }),
  updateEscalation: (id: string, status: Escalation["status"], note?: string) =>
    request<Escalation>(p(`/escalations/${id}`), { method: "PATCH", body: { status, note } }),
  agents: () => request<AgentsOverview>(p("/agents")),
  audit: (query?: Query) => request<{ items: AuditLog[]; total: number }>(p("/audit"), { query }),
  settings: () => request<AppSettings>(p("/settings")),
};
