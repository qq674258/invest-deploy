import { CHART_DEFAULT_LIMIT } from "./chart-range";
import type { SiteConfig } from "./site-types";
import type {
  DashboardResponse,
  FundHoldingsResponse,
  FundManagersResponse,
  FundNavResponse,
  FundPerformanceResponse,
  FundListResponse,
  FundSummary,
  FundTradingRulesResponse,
  Instrument,
  LumpSumMeta,
  LumpSumResult,
  MarketChartResponse,
} from "./types";

const BASE = "";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    // 由 React Query 控制 1 分钟 staleTime，避免浏览器 HTTP 缓存旧数据
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  siteConfig: () => fetchJson<SiteConfig>("/api/v1/site/config"),
  health: () => fetchJson<{ status: string; data: unknown }>("/api/v1/health"),
  instruments: () => fetchJson<Instrument[]>("/api/v1/instruments"),
  dashboard: (refresh = false) =>
    fetchJson<DashboardResponse>(
      `/api/v1/dashboard${refresh ? "?refresh=true" : ""}`
    ),
  marketChart: (id: string, limit = CHART_DEFAULT_LIMIT, refresh = false) =>
    fetchJson<MarketChartResponse>(
      `/api/v1/market/${id}/chart?limit=${limit}${refresh ? "&refresh=true" : ""}`
    ),
  returnStats: (id: string) =>
    fetchJson<{
      instrument_id: string;
      annualized_return_pct: number;
      sample_years: number;
      source: string;
    }>(`/api/v1/market/${id}/return-stats`),

  lumpSumMeta: (id: string) =>
    fetchJson<LumpSumMeta>(`/api/v1/market/${id}/lump-sum/meta`),

  lumpSumCalc: (id: string, buyDate: string, amount: number) =>
    fetchJson<LumpSumResult>(
      `/api/v1/market/${id}/lump-sum?buy_date=${encodeURIComponent(buyDate)}&amount=${amount}`
    ),

  fundSummary: (id: string) => fetchJson<FundSummary>(`/api/v1/funds/${id}`),
  fundList: (params?: {
    q?: string;
    code?: string;
    market?: string;
    sector?: string;
  }) => {
    const q = new URLSearchParams();
    if (params?.q?.trim()) q.set("q", params.q.trim());
    if (params?.code?.trim()) q.set("code", params.code.trim());
    if (params?.market?.trim()) q.set("market", params.market.trim());
    if (params?.sector?.trim()) q.set("sector", params.sector.trim());
    const qs = q.toString();
    return fetchJson<FundListResponse>(`/api/v1/funds${qs ? `?${qs}` : ""}`);
  },
  fundPerformance: (id: string, limit = CHART_DEFAULT_LIMIT) =>
    fetchJson<FundPerformanceResponse>(
      `/api/v1/funds/${id}/performance?limit=${limit}`
    ),
  fundNav: (id: string, limit = 30, offset = 0) =>
    fetchJson<FundNavResponse>(
      `/api/v1/funds/${id}/nav?limit=${limit}&offset=${offset}`
    ),
  fundHoldings: (id: string) =>
    fetchJson<FundHoldingsResponse>(`/api/v1/funds/${id}/holdings`),
  fundManagers: (id: string) =>
    fetchJson<FundManagersResponse>(`/api/v1/funds/${id}/managers`),
  fundTradingRules: (id: string) =>
    fetchJson<FundTradingRulesResponse>(`/api/v1/funds/${id}/trading-rules`),
};
