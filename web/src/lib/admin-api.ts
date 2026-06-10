import { clearAdminToken, getAdminToken } from "./admin-auth";

async function adminFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAdminToken();
  if (!token && !path.endsWith("/login")) {
    throw new Error("请先登录管理后台");
  }
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
    cache: "no-store",
  });
  if (res.status === 401) {
    clearAdminToken();
    if (
      typeof window !== "undefined" &&
      !window.location.pathname.startsWith("/admin/login")
    ) {
      window.location.href = "/admin/login";
    }
    throw new Error("登录已失效，请重新登录管理后台");
  }
  if (!res.ok) {
    let detail: unknown = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? body.message ?? detail;
    } catch {
      const text = await res.text();
      if (text) detail = text.slice(0, 500);
    }
    const err = new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail)
    ) as Error & { status?: number; detail?: unknown };
    err.status = res.status;
    err.detail = detail;
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export type CrawlSourcesConfig = {
  defaults?: Record<string, number | string | boolean>;
  endpoints?: Record<string, string>;
  multpl_slugs?: Record<string, string>;
  providers?: Record<string, unknown>;
  jobs?: Record<string, unknown[]>;
};

export type AlertEmailConfig = {
  enabled?: boolean;
  smtp_host?: string;
  smtp_port?: number;
  smtp_use_ssl?: boolean;
  smtp_user?: string;
  smtp_password?: string;
  smtp_password_set?: boolean;
  from_addr?: string;
  to_addrs?: string[];
};

export type AlertDrawdownConfig = {
  enabled?: boolean;
  instrument_ids?: string[];
  lookback_days?: number;
  thresholds_pct?: number[];
  recover_above_pct?: number;
};

export type AlertConfig = {
  email?: AlertEmailConfig;
  drawdown?: AlertDrawdownConfig;
};

export type SchedulerStatus = {
  running?: boolean;
  auto_crawl_enabled?: boolean;
  auto_crawl_time?: string;
  auto_crawl_timezone?: string;
  auto_crawl_incremental?: boolean;
  auto_crawl_include_funds?: boolean;
  auto_crawl_run_alerts?: boolean;
  drawdown_alert_enabled?: boolean;
  email_enabled?: boolean;
  jobs?: { id: string; next_run?: string | null }[];
  server_time?: string;
};

export type SiteConfigAdmin = {
  title?: string;
  frontend_login_enabled?: boolean;
};

export type SiteConfigPublic = {
  title: string;
  frontend_login_enabled: boolean;
};

export type SiteUser = {
  id: number;
  phone: string;
  display_name?: string | null;
  enabled: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

export type LoginLog = {
  id: number;
  phone: string;
  login_type: string;
  success: boolean;
  ip?: string | null;
  user_agent?: string | null;
  failure_reason?: string | null;
  created_at?: string | null;
};

export type DrawdownAlertResult = {
  status: string;
  reason?: string;
  checked?: {
    instrument_id: string;
    display_name?: string;
    drawdown_pct?: number;
    notified?: number[];
    error?: string;
  }[];
  alerts?: { instrument_id: string; threshold_pct: number; message: string }[];
  emails_sent?: number;
  errors?: string[];
  dry_run?: boolean;
};

export type CrawlTarget = {
  instrument_id: string;
  display_name: string;
  job?: string;
};

export type FundManagerOnFund = {
  mgr_id: string;
  name?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  tenure_days?: number | null;
  tenure_return_pct?: number | null;
  is_current?: boolean;
};

export type FundResolveResult = {
  fund_code: string;
  display_name?: string | null;
  fund_manager?: string | null;
  fund_company?: string | null;
  fund_type?: string | null;
  establish_date?: string | null;
  manager_ids: string[];
  managers: FundManagerOnFund[];
};

export type AdminInstrument = {
  instrument_id: string;
  display_name: string;
  asset_class: string;
  fund_code?: string;
  market?: string;
  sector?: string;
  crawl_enabled?: boolean;
  nav_lookback?: string;
  enabled?: boolean;
  fund_manager?: string;
  fund_company?: string;
  fund_type?: string;
  establish_date?: string;
  manager_ids?: string[];
  managers_on_fund?: FundManagerOnFund[];
  admin_managed?: boolean;
  data?: { rows?: number; last_date?: string };
};

export type FundsListResponse = {
  total: number;
  items: AdminInstrument[];
};

export type FundSearchParams = {
  q?: string;
  code?: string;
  market?: string;
  sector?: string;
};

export type CrawlLogLine = {
  ts: string;
  level: "info" | "warn" | "error";
  message: string;
  progress?: number | null;
};

export type CrawlResult = {
  instrument_id?: string;
  fund_code?: string;
  rows: number;
  errors: string[];
  status: string;
  logs?: CrawlLogLine[];
  meta?: Record<string, unknown>;
  nav_lookback?: string;
};

export type CrawlJobState = {
  instrumentId: string;
  displayName?: string;
  status: "idle" | "running" | "success" | "partial" | "error";
  progress: number;
  logs: CrawlLogLine[];
  result?: CrawlResult;
  errorMessage?: string;
};

type CrawlStreamHandlers = {
  onLog: (line: CrawlLogLine) => void;
};

async function parseSseStream(
  res: Response,
  handlers: CrawlStreamHandlers
): Promise<CrawlResult> {
  const reader = res.body?.getReader();
  if (!reader) throw new Error("无法读取采集流");

  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult: CrawlResult | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const line = chunk.trim();
      if (!line.startsWith("data:")) continue;
      const jsonStr = line.replace(/^data:\s*/, "");
      if (!jsonStr) continue;
      const payload = JSON.parse(jsonStr) as {
        type: string;
        ts?: string;
        level?: string;
        message?: string;
        progress?: number;
        result?: CrawlResult;
        code?: string;
      };
      if (payload.type === "log" && payload.message) {
        handlers.onLog({
          ts: payload.ts ?? new Date().toISOString(),
          level: (payload.level as CrawlLogLine["level"]) ?? "info",
          message: payload.message,
          progress: payload.progress ?? null,
        });
      } else if (payload.type === "done" && payload.result) {
        finalResult = payload.result;
      } else if (payload.type === "error") {
        throw new Error(payload.message ?? payload.code ?? "采集失败");
      }
    }
  }

  if (!finalResult) throw new Error("采集流意外结束");
  return finalResult;
}

export const adminApi = {
  login: (username: string, password: string) =>
    adminFetch<{ token: string; username: string }>("/api/v1/admin/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  crawlTargets: () =>
    adminFetch<{
      indices: CrawlTarget[];
      funds: AdminInstrument[];
      default_lookback_days: number;
    }>("/api/v1/admin/crawl-targets"),

  getCrawlConfig: () =>
    adminFetch<{
      config: CrawlSourcesConfig;
      meta: {
        base_path: string;
        override_path: string;
        override_exists: boolean;
        url_fields: string[];
      };
      lookback_days: number;
    }>("/api/v1/admin/crawl/config"),

  saveCrawlConfig: (config: CrawlSourcesConfig, confirmUrlChanges: boolean) =>
    adminFetch<{
      status: string;
      config: CrawlSourcesConfig;
      lookback_days: number;
      url_changes_applied?: { field: string; from: string; to: string }[];
    }>("/api/v1/admin/crawl/config", {
      method: "PUT",
      body: JSON.stringify({ config, confirm_url_changes: confirmUrlChanges }),
    }),

  resetCrawlConfig: () =>
    adminFetch<{ status: string; config: CrawlSourcesConfig }>(
      "/api/v1/admin/crawl/config/override",
      { method: "DELETE" }
    ),

  getAlertConfig: () =>
    adminFetch<{
      config: AlertConfig;
      indices: { instrument_id: string; display_name: string }[];
      scheduler: SchedulerStatus;
    }>("/api/v1/admin/alerts/config"),

  saveAlertConfig: (config: AlertConfig) =>
    adminFetch<{ status: string; config: AlertConfig }>("/api/v1/admin/alerts/config", {
      method: "PUT",
      body: JSON.stringify({ config }),
    }),

  resetAlertConfig: () =>
    adminFetch<{ status: string; config: AlertConfig }>(
      "/api/v1/admin/alerts/config/override",
      { method: "DELETE" }
    ),

  testAlertEmail: (body?: { subject?: string; body?: string }) =>
    adminFetch<{ status: string }>("/api/v1/admin/alerts/test-email", {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),

  testDrawdownAlertEmail: () =>
    adminFetch<{ status: string }>("/api/v1/admin/alerts/test-drawdown-email", {
      method: "POST",
    }),

  checkDrawdownAlerts: (dryRun = false) =>
    adminFetch<DrawdownAlertResult>(
      `/api/v1/admin/alerts/check-drawdown?dry_run=${dryRun ? "true" : "false"}`,
      { method: "POST" }
    ),

  schedulerStatus: () =>
    adminFetch<SchedulerStatus>("/api/v1/admin/scheduler/status"),

  runSchedulerNow: () =>
    adminFetch<{ status: string; scheduler: SchedulerStatus }>(
      "/api/v1/admin/scheduler/run-now",
      { method: "POST" }
    ),

  crawlInstrument: (id: string, body?: { lookback_days?: number; nav_lookback?: string; recent_bars?: number }) =>
    adminFetch<CrawlResult>(`/api/v1/admin/crawl/instrument/${id}`, {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),

  /** SSE 实时日志 + 最终结果 */
  crawlInstrumentStream: async (
    id: string,
    handlers: CrawlStreamHandlers,
    body?: { lookback_days?: number; nav_lookback?: string; recent_bars?: number }
  ): Promise<CrawlResult> => {
    const token = getAdminToken();
    if (!token) throw new Error("请先登录管理后台");

    const res = await fetch(`/api/v1/admin/crawl/instrument/${id}/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body ?? {}),
      cache: "no-store",
    });

    if (res.status === 401) {
      clearAdminToken();
      if (
        typeof window !== "undefined" &&
        !window.location.pathname.startsWith("/admin/login")
      ) {
        window.location.href = "/admin/login";
      }
      throw new Error("登录已失效，请重新登录管理后台");
    }
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const errBody = await res.json();
        detail = errBody.detail ?? errBody.message ?? detail;
      } catch {
        const text = await res.text();
        if (text) detail = text.slice(0, 200);
      }
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }

    return parseSseStream(res, handlers);
  },

  crawlJob: (jobId: string) =>
    adminFetch<unknown>(`/api/v1/admin/crawl/job/${jobId}`, { method: "POST" }),

  instruments: () => adminFetch<AdminInstrument[]>("/api/v1/admin/instruments"),

  funds: (params?: FundSearchParams) => {
    const q = new URLSearchParams();
    if (params?.q?.trim()) q.set("q", params.q.trim());
    if (params?.code?.trim()) q.set("code", params.code.trim());
    if (params?.market?.trim()) q.set("market", params.market.trim());
    if (params?.sector?.trim()) q.set("sector", params.sector.trim());
    const qs = q.toString();
    return adminFetch<FundsListResponse>(
      `/api/v1/admin/funds${qs ? `?${qs}` : ""}`
    );
  },

  getFund: (id: string) => adminFetch<AdminInstrument>(`/api/v1/admin/funds/${id}`),

  resolveFund: (fund_code: string) =>
    adminFetch<FundResolveResult>("/api/v1/admin/funds/resolve", {
      method: "POST",
      body: JSON.stringify({ fund_code }),
    }),

  getFundManagers: (id: string) =>
    adminFetch<{
      instrument_id: string;
      manager_ids: string[];
      managers_on_fund: FundManagerOnFund[];
      profiles: Record<string, unknown>[];
    }>(`/api/v1/admin/funds/${id}/managers`),

  createFund: (body: Record<string, unknown>) =>
    adminFetch<{ instrument_id: string }>("/api/v1/admin/funds", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateFund: (id: string, body: Record<string, unknown>) =>
    adminFetch<{ instrument_id: string }>(`/api/v1/admin/funds/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  deleteFund: (id: string) =>
    adminFetch<{ status: string }>(`/api/v1/admin/funds/${id}`, { method: "DELETE" }),

  listData: (id: string, params?: { limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    return adminFetch<{
      data_type: string;
      total: number;
      rows: Record<string, unknown>[];
    }>(`/api/v1/admin/data/${id}?${q}`);
  },

  dedupe: (id: string) =>
    adminFetch<{ removed: number }>(`/api/v1/admin/data/${id}/dedupe`, {
      method: "POST",
    }),

  deleteOhlcv: (ids: number[]) =>
    adminFetch<{ deleted: number }>("/api/v1/admin/data/ohlcv", {
      method: "DELETE",
      body: JSON.stringify({ ids }),
    }),

  deleteNav: (ids: number[]) =>
    adminFetch<{ deleted: number }>("/api/v1/admin/data/nav", {
      method: "DELETE",
      body: JSON.stringify({ ids }),
    }),

  audits: () =>
    adminFetch<
      {
        id: number;
        job_id: string;
        status: string;
        rows_upserted: number;
        errors: string[];
        started_at: string;
      }[]
    >("/api/v1/admin/audits"),

  getSiteConfig: () =>
    adminFetch<{
      config: { site?: SiteConfigAdmin };
      public: SiteConfigPublic;
    }>("/api/v1/admin/site/config"),

  saveSiteConfig: (config: { site?: SiteConfigAdmin }) =>
    adminFetch<{ status: string; config: unknown; public: SiteConfigPublic }>(
      "/api/v1/admin/site/config",
      { method: "PUT", body: JSON.stringify({ config }) }
    ),

  listSiteUsers: () =>
    adminFetch<{ items: SiteUser[] }>("/api/v1/admin/site-users"),

  createSiteUser: (body: {
    phone: string;
    password: string;
    display_name?: string;
    enabled?: boolean;
  }) =>
    adminFetch<{ status: string; user: SiteUser }>("/api/v1/admin/site-users", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateSiteUser: (
    id: number,
    body: {
      phone?: string;
      password?: string;
      display_name?: string;
      enabled?: boolean;
    }
  ) =>
    adminFetch<{ status: string; user: SiteUser }>(
      `/api/v1/admin/site-users/${id}`,
      { method: "PUT", body: JSON.stringify(body) }
    ),

  deleteSiteUser: (id: number) =>
    adminFetch<{ status: string }>(`/api/v1/admin/site-users/${id}`, {
      method: "DELETE",
    }),

  listLoginLogs: (params?: { limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    const qs = q.toString();
    return adminFetch<{
      items: LoginLog[];
      total: number;
      limit: number;
      offset: number;
    }>(`/api/v1/admin/login-logs${qs ? `?${qs}` : ""}`);
  },

  deleteLoginLog: (id: number) =>
    adminFetch<{ status: string }>(`/api/v1/admin/login-logs/${id}`, {
      method: "DELETE",
    }),
};
