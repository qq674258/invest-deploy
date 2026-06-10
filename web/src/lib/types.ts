export interface Instrument {
  instrument_id: string;
  display_name: string;
  asset_class: string;
  enabled: boolean;
  fund_code?: string;
  market?: string;
  sector?: string;
}

export interface DashboardItem {
  instrument_id: string;
  display_name: string;
  asset_class?: string;
  fund_code?: string;
  market?: string;
  sector?: string;
  fund_manager?: string;
  latest_nav?: number | null;
  latest_daily_return_pct?: number | null;
  data: { last_date?: string; rows?: number };
}

export interface DashboardResponse {
  as_of: string;
  items: DashboardItem[];
  health: Record<string, unknown>;
}

export interface FundPeriodReturn {
  period_id: string;
  label: string;
  return_pct?: number | null;
  peer_avg_pct?: number | null;
  benchmark_pct?: number | null;
  rank?: string | null;
  peer_count?: string | null;
}

export interface FundListItem {
  instrument_id: string;
  display_name: string;
  fund_code?: string;
  market?: string;
  sector?: string;
  fund_manager?: string;
  latest_nav_date?: string | null;
  nav_rows: number;
  returns: {
    ytd?: number | null;
    "3m"?: number | null;
    "6m"?: number | null;
    "1y"?: number | null;
    "3y"?: number | null;
    "5y"?: number | null;
    si?: number | null;
  };
}

export interface FundListResponse {
  total: number;
  items: FundListItem[];
}

export interface FundSummary {
  instrument_id: string;
  fund_code: string;
  display_name: string;
  market?: string;
  sector?: string;
  fund_type?: string;
  fund_company?: string;
  fund_manager?: string;
  establish_date?: string;
  latest_nav?: number | null;
  latest_nav_date?: string | null;
  daily_return_pct?: number | null;
  nav_rows?: number;
  period_returns?: FundPeriodReturn[];
  trading_rules?: Record<string, unknown>;
}

export interface FundPerformanceResponse {
  instrument_id: string;
  chart: {
    dates: string[];
    nav: number[];
    normalized: number[];
    base_date?: string | null;
  };
  computed_periods: FundPeriodReturn[];
  official_periods: FundPeriodReturn[];
}

export interface FundNavRow {
  nav_date: string;
  nav: number;
  acc_nav?: number | null;
  daily_return?: number | null;
}

export interface FundNavResponse {
  total: number;
  rows: FundNavRow[];
}

export interface FundHoldingRow {
  symbol?: string | null;
  name: string;
  weight_pct?: number | null;
  change_pct?: number | null;
  industry?: string | null;
}

export interface FundHoldingsResponse {
  instrument_id: string;
  fund_code: string;
  report_date?: string | null;
  holdings: FundHoldingRow[];
  disclaimer?: string;
}

export interface FundManagersResponse {
  instrument_id: string;
  manager_ids: string[];
  managers_on_fund: FundManagerOnFund[];
  profiles: FundManagerProfile[];
}

export interface FundTradingRulesResponse {
  instrument_id: string;
  rules: Record<string, unknown>;
  source?: string;
}

export interface FundManagerProfile {
  mgr_id: string;
  name?: string | null;
  company?: string | null;
  resume?: string | null;
  photo_url?: string | null;
  experience_years?: string | null;
  managed_fund_codes?: string[];
  managed_fund_names?: string[];
  fetched_at?: string | null;
}

export interface FundManagerOnFund {
  mgr_id: string;
  name?: string | null;
  start_date?: string | null;
  tenure_days?: number | null;
  tenure_return_pct?: number | null;
  is_current?: boolean;
}

export interface MacroSnapshotPoint {
  value: number | null;
  date?: string | null;
  unit?: string | null;
  label?: string | null;
}

export interface MacroSnapshot {
  pe_ttm?: MacroSnapshotPoint;
  vix?: MacroSnapshotPoint;
  cpi?: MacroSnapshotPoint;
  pce?: MacroSnapshotPoint;
}

export interface MarketChartResponse {
  instrument_id: string;
  display_name: string;
  dates: string[];
  candles: number[][];
  volume: number[];
  indicators: Record<string, (number | null)[]>;
  metric_ids: string[];
  macro_snapshot?: MacroSnapshot;
}

export interface LumpSumMeta {
  instrument_id: string;
  data_start: string;
  data_end: string;
  latest_price: number;
}

export interface LumpSumResult {
  instrument_id: string;
  buy_date_requested: string;
  buy_date: string;
  buy_price: number;
  latest_date: string;
  latest_price: number;
  amount: number;
  final_value: number;
  profit: number;
  return_pct: number;
  annualized_return_pct: number;
  holding_days: number;
  holding_years: number;
  data_start: string;
  data_end: string;
  date_snapped?: boolean;
  context?: AllInContext;
}

export interface AllInSignalTier {
  id: string;
  label: string;
  range: string;
  advice: string;
}

export interface AllInSignalBlock {
  buy?: number | null;
  latest?: number | null;
  buy_pct?: number | null;
  latest_pct?: number | null;
  buy_high?: number | null;
  latest_high?: number | null;
  buy_tier_id?: string | null;
  buy_label?: string | null;
  latest_tier_id?: string | null;
  latest_label?: string | null;
  advice?: string | null;
  tiers?: AllInSignalTier[];
  note?: string | null;
  unit?: string;
}

export interface AllInContext {
  drawdown_window?: string;
  drawdown_window_days?: number;
  drawdown_window_label?: string;
  signals: {
    drawdown?: AllInSignalBlock;
  };
}

