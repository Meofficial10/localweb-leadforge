// API client against the LeadForge backend.
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export const API_TOKEN =
  process.env.NEXT_PUBLIC_API_TOKEN ||
  (typeof window !== "undefined" ? (window as any).__LEADFORGE_TOKEN__ || "" : "");

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      detail = (await res.text()) || res.statusText;
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function auth(): Record<string, string> {
  return { Authorization: `Bearer ${API_TOKEN}` };
}

export function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(path, API_BASE);
  if (params) Object.entries(params).forEach(([k, v]) => v && url.searchParams.set(k, v));
  return fetch(url.toString(), { headers: auth() }).then(handle<T>);
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return fetch(API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...auth() },
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then(handle<T>);
}

export function patch<T>(path: string, body?: unknown): Promise<T> {
  return fetch(API_BASE + path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...auth() },
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then(handle<T>);
}

export function del<T>(path: string): Promise<T> {
  return fetch(API_BASE + path, {
    method: "DELETE",
    headers: auth(),
  }).then(handle<T>);
}

// typed helpers
export const campaignsApi = {
  list: () => get<Campaign[]>("/campaigns"),
  get: (id: string) => get<Campaign>(`/campaigns/${id}`),
  create: (body: CampaignInput) => post<Campaign>("/campaigns", body),
  update: (id: string, body: Partial<CampaignInput>) => patch<Campaign>(`/campaigns/${id}`, body),
  del: (id: string) => del(`/campaigns/${id}`),
  run: (id: string) => post(`/campaigns/${id}/run`),
  pause: (id: string, paused: boolean) => patch<Campaign>(`/campaigns/${id}/pause?paused=${paused}`, undefined),
  duplicate: (id: string) => post<Campaign>(`/campaigns/${id}/duplicate`),
};


export const queueApi = {
  list: () => get<Draft[]>("/queue"),
  approve: (id: string) => post<Draft>(`/queue/${id}/approve`),
  skip: (id: string) => post<Draft>(`/queue/${id}/skip`),
  edit: (id: string, body: { subject?: string; body?: string }) => patch<Draft>(`/queue/${id}`, body),
  regenerate: (id: string) => post<Draft>(`/queue/${id}/regenerate`),
  bulkApprove: (ids: string[]) => post<{ approved: number }>("/queue/bulk-approve", { ids }),
};
export const leadsApi = {
  list: (params: Record<string, string>) => get<PagedLeads>(`/leads`, params),
  get: (id: string) => get<LeadDetail>(`/leads/${id}`),
  del: (id: string) => del(`/leads/${id}`),
  bulkDelete: (ids: string[]) => post<{ deleted: number }>("/leads/bulk/delete", { ids }),
  bulkSuppress: (ids: string[], reason?: string) => post<{ suppressed: number }>("/leads/bulk/suppress", { ids, reason }),
  regenerateDemo: (id: string) => post(`/leads/${id}/demo/regenerate`),
};

export interface PagedLeads {
  items: Lead[];
  total: number;
  page: number;
  page_size: number;
}

export const inboxApi = {
  list: (scope: string = "unhandled") => get<InboxItem[]>(`/inbox?scope=${scope}`),
  handle: (id: string) => post<InboxItem>(`/inbox/${id}/handle`),
  takeOver: (id: string) => post<InboxItem>(`/inbox/${id}/take-over`),
};

export const callsApi = {
  list: () => get<CallItem[]>("/calls"),
};

export const complianceApi = {
  status: () => get<SystemStatus>("/system/status"),
  setPause: (paused: boolean) => post("/system/pause", { paused }),
  suppress: (body: { kind: string; value: string; reason?: string }) =>
    post("/suppression", body),
  listSuppression: (search?: string) => get<SuppressionItem[]>("/suppression", { search: search || "" }),
  removeSuppression: (id: string, reason?: string) => del(`/suppression/${id}?reason=${encodeURIComponent(reason || "")}`),
  audit: (params: Record<string, string>) => get<AuditItem[]>("/system/audit", params),
};

export const integrationsApi = {
  list: () => get<{ cards: IntegrationCard[]; health: IntegrationHealth; required_ids: string[]; force_dry_run: boolean }>("/integrations"),
  setSecret: (key: string, value: string) => post("/integrations/secrets", { key, value }),
  clearSecret: (key: string) => del(`/integrations/secrets/${key}`),
  test: (id: string) => post<{ ok: boolean; message: string; detail?: string; latency_ms?: number; at?: string }>(`/integrations/${id}/test`),
  configure: (id: string, values: Record<string, unknown>) => post<{ config: Record<string, unknown>; test: { ok: boolean; message: string; detail?: string; latency_ms?: number } }>(`/integrations/${id}/configure`, { values }),
  configureIntegration: (id: string, values: Record<string, unknown>) => post<{ config: Record<string, unknown>; test: { ok: boolean; message: string; detail?: string; latency_ms?: number } }>(`/integrations/${id}/configure`, { values }),
  models: (provider: string, baseUrl?: string) => get<{ models: string[] }>(`/integrations/llm/models`, { provider, base_url: baseUrl || "" }),
};

export const settingsApi = {
  get: () => get<AppSettings>("/settings"),
  update: (values: Record<string, unknown>) => patch<AppSettings>("/settings", { values }),
};

export const systemApi = {
  health: () => get<{ status: string; env: string }>("/health"),
  status: () => get<SystemStatus>("/system/status"),
  metrics: () => get<Metrics>("/system/metrics"),
  campaignModes: (campaignId?: string) =>
    get<{ effective: Record<string, string> }>("/system/campaign-modes", { campaign_id: campaignId || "" }),
  audit: (params?: Record<string, string>) => get<any[]>("/system/audit", params),
};

// ---------- types ----------
export interface Campaign {
  id: string; name: string; country: string; city: string;
  area_radius_km?: number | null; categories: string[]; lead_source: string;
  daily_email_cap: number; daily_call_cap: number; max_leads_per_run?: number | null;
  send_window?: Record<string, any> | null; timezone: string;
  warm_up_schedule?: Record<string, any> | null; followup_delay_days: number;
  approval_mode: string; cron_schedule?: Record<string, any> | null;
  mode: string; is_paused: boolean;
  created_at?: string | null; updated_at?: string | null;
}
export type CampaignInput = Partial<Campaign> & { name: string; city: string };

export interface Lead {
  id: string; campaign_id?: string | null; name: string; category?: string | null;
  address?: string | null; status: string; contact_type?: string | null;
  has_website: boolean; rating?: number | null; review_count?: number | null;
  source: string;
  contacts?: { id: string; kind: string; value: string; source_url?: string }[];
}
export interface LeadDetail extends Lead {
  demo?: { id: string; preview_url?: string | null; deploy_status: string }[];
  contacts?: { id: string; kind: string; value: string; source?: string }[];
  demo_sites?: { id: string; preview_url?: string | null; deploy_status: string }[];
  profile?: any;
  messages?: { id: string; channel?: string; direction?: string; subject?: string | null; status: string; sequence_step?: number; intent?: string | null; created_at?: string | null }[];
  calls?: { id: string; outcome?: string | null; duration_sec?: number | null; started_at?: string | null; transcript?: string | null; recording_url?: string | null; ai_disclosed?: boolean; dnc_checked_at?: string | null }[];
}
export interface Draft {
  id: string; lead_id: string; lead_name: string; lead_category?: string | null;
  subject?: string | null; body?: string | null; status: string; sequence_step: number;
  campaign_id?: string | null; compliance: { ok: boolean; reasons: string[] };
  created_at?: string | null;
}
export interface InboxItem {
  id: string; lead_id: string | null; lead_name: string; lead_email?: string | null;
  subject?: string | null; content?: string | null; intent: string;
  handled: boolean; status: string; received_at?: string | null;
}
export interface CallItem {
  id: string; lead_id: string; lead_name: string; outcome?: string | null;
  duration_sec?: number | null; ai_disclosed: boolean; started_at?: string | null;
  transcript?: string | null; dnc_checked_at?: string | null; recording_url?: string | null;
}
export interface SuppressionItem {
  id: string; kind: string; value: string; reason?: string | null; created_at?: string | null;
}
export interface AuditItem {
  id: number; action: string; lead_id?: string | null; detail?: any; created_at?: string | null;
}
export interface SystemStatus {
  paused: boolean; force_dry_run: boolean;
  channels: Record<string, { paused: boolean; effective_mode: string }>;
  bounce_rate: number; complaint_rate: number; bounce_threshold: number; complaint_threshold: number;
}
export interface Metrics {
  kpis: Record<string, number>;
  funnel: Record<string, number>;
  leads_per_day: { date: string; count: number }[];
}
export interface IntegrationStatus {
  state: "disabled" | "not_configured" | "configured" | "connected" | "error";
  label: string; color: "gray" | "yellow" | "green" | "red"; icon: string;
  detail: string; last_checked?: string | null;
}
export interface ProviderDef {
  id: string; label: string; needs_key: boolean; key_secret_key: string;
  base_url_default: string; base_url_editable: boolean; static_models: string[];
  probe_url?: string | null; note: string;
}
export interface FieldDef {
  key: string; label: string; type: string; placeholder: string; help: string;
  options?: string[] | null; default?: unknown;
}
export interface IntegrationCard {
  id: string; name: string; kind: string; required: boolean; description: string;
  providers: ProviderDef[]; fields: FieldDef[];
  provider: string; config: Record<string, unknown>;
  status: IntegrationStatus; secret: SecretMeta | null;
}
export interface SecretMeta {
  key: string; is_set: boolean; masked: string; last_verified_at?: string | null;
}
export interface IntegrationHealth {
  working: number; required: number; ok: boolean; message: string;
  checklist: { id: string; name: string; required: boolean; state: string; label: string; detail: string; ok: boolean }[];
}
export interface AppSettings {
  daily_email_cap: number; daily_call_cap: number;
  send_window: Record<string, any>; warm_up_schedule: Record<string, any>;
  followup_delay_days: number; approval_mode: string;
  bounce_tolerance: number; complaint_tolerance: number;
  budgets: Record<string, number>;
  branding: Record<string, string>;
  tokens: Record<string, string[]>;
}