// Single API client for the LifeOS backend (Section 0.4 contract).
// JWT is stored in localStorage (hackathon scope) and attached to every request.
// KNOWN LIMITATION (flag for docs/threat-model.md): localStorage tokens are
// readable by any XSS on the page; production should use httpOnly cookies.

const BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

const ACCESS_KEY = "lifeos_access_token";
const REFRESH_KEY = "lifeos_refresh_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_KEY);
}

export function setTokens(access: string, refresh?: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ACCESS_KEY, access);
  if (refresh) window.localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type ReqOpts = { method?: string; body?: unknown; auth?: boolean; form?: FormData };

async function request<T>(path: string, opts: ReqOpts = {}): Promise<T> {
  const { method = "GET", body, auth = true, form } = opts;
  const headers: Record<string, string> = {};
  if (auth) {
    const t = getToken();
    if (t) headers["Authorization"] = `Bearer ${t}`;
  }
  let payload: BodyInit | undefined;
  if (form) {
    payload = form; // browser sets multipart boundary
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const res = await fetch(`${BASE}${path}`, { method, headers, body: payload });

  if (res.status === 401) {
    // Expired/invalid token -> clear and signal so the app can redirect to /login.
    clearTokens();
    throw new ApiError(401, "Session expired. Please log in again.");
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const data = await res.json();
      // FastAPI returns { detail: "..." } — surface the REAL backend message.
      if (typeof data?.detail === "string") detail = data.detail;
      else if (Array.isArray(data?.detail)) detail = data.detail[0]?.msg ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---------- Types (match backend response shapes) ----------
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}
export interface DocumentSummary {
  id: string;
  filename: string;
  doc_type: string;
  upload_status: string;
  created_at: string;
}
export interface ExtractedField {
  id: string;
  field_name: string;
  field_value: string | null;
  field_type: string;
  source_span: Record<string, number> | null;
  confidence: number | null;
}
export interface DocumentDetail extends DocumentSummary {
  ocr_text: string | null;
  extracted_fields: ExtractedField[];
  agent_trace: Array<Record<string, unknown>>;
}
export interface Reminder {
  id: string;
  document_id: string | null;
  title: string;
  due_date: string | null;
  status: string;
  created_at: string;
}
export interface Insight {
  id: string;
  type: string;
  description: string | null;
  related_reminder_ids: string[] | null;
  severity: string;
  created_at: string;
}
export interface ChatMessage {
  id: string;
  role: string;
  content: string | null;
  created_at: string;
}
export interface ChatResponse {
  conversation_id: string;
  message: ChatMessage;
  intent: string;
  citations: Array<{ document_id: string; filename: string }>;
}
export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
}

// ---------- Endpoint wrappers (Section 0.4) ----------
export const api = {
  // Auth
  register: (email: string, password: string, full_name?: string) =>
    request<{ id: string }>("/auth/register", {
      method: "POST",
      auth: false,
      body: { email, password, full_name },
    }),
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      auth: false,
      body: { email, password },
    }),

  // Documents
  listDocuments: () => request<DocumentSummary[]>("/documents"),
  getDocument: (id: string) => request<DocumentDetail>(`/documents/${id}`),
  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentDetail>("/documents/upload", { method: "POST", form });
  },
  deleteDocument: (id: string) =>
    request<void>(`/documents/${id}`, { method: "DELETE" }),
  sharedWithMe: () => request<DocumentSummary[]>("/documents/shared-with-me"),
  shareDocument: (
    id: string,
    shared_with_email: string,
    permission: "view" | "edit" = "view",
    expires_at?: string | null
  ) =>
    request<unknown>(`/documents/${id}/share`, {
      method: "POST",
      body: { shared_with_email, permission, expires_at: expires_at ?? null },
    }),

  // Reminders
  listReminders: (status?: string) =>
    request<Reminder[]>(`/reminders${status ? `?status=${status}` : ""}`),
  updateReminder: (id: string, status: "pending" | "done" | "dismissed") =>
    request<Reminder>(`/reminders/${id}`, { method: "PATCH", body: { status } }),

  // Insights
  listInsights: (refresh = false) =>
    request<Insight[]>(`/insights${refresh ? "?refresh=true" : ""}`),

  // Chat
  chat: (message: string, conversation_id?: string) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: { message, conversation_id: conversation_id ?? null },
    }),
  listConversations: () => request<Conversation[]>("/chat/conversations"),
  getMessages: (conversationId: string) =>
    request<ChatMessage[]>(`/chat/conversations/${conversationId}/messages`),
};
