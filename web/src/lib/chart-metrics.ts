/** 指标展示配置：子图分组与中文名 */
export const METRIC_LABELS: Record<string, string> = {
  ma50: "MA50",
  ma200: "MA200",
  macd_hist: "MACD柱",
  price_vs_ma200: "价格/MA200",
  rsi14: "RSI14",
  mom_12_1: "12-1动量",
  vix: "VIX",
  atr_pct: "ATR%",
  drawdown_52w: "52周回撤",
  pe_ttm: "PE (TTM)",
  pe_ttm_percentile_5y: "PE五年分位",
  price_percentile_5y: "价格五年分位",
  us10y: "美债10Y",
  dxy: "美元指数",
};

/** 主图叠加均线（默认隐藏，点击显示） */
export const PRICE_OVERLAYS = ["ma50", "ma200"] as const;

/** 子图（默认隐藏，点击显示） */
export const INDICATOR_PANELS: {
  id: string;
  title: string;
  metrics: string[];
  yMin?: number;
  yMax?: number;
}[] = [
  { id: "rsi", title: "RSI14", metrics: ["rsi14"], yMin: 0, yMax: 100 },
  { id: "macd", title: "MACD", metrics: ["macd_hist"] },
  { id: "vol", title: "波动", metrics: ["vix", "drawdown_52w", "atr_pct"] },
  { id: "mom", title: "动量", metrics: ["mom_12_1", "price_vs_ma200"] },
  {
    id: "val",
    title: "估值分位",
    metrics: ["price_percentile_5y", "pe_ttm_percentile_5y"],
    yMin: 0,
    yMax: 100,
  },
  { id: "macro", title: "宏观", metrics: ["us10y", "dxy"] },
];

export const OVERLAY_COLORS: Record<string, string> = {
  ma50: "#f59e0b",
  ma200: "#a855f7",
};

export const SERIES_COLORS = [
  "#3b82f6",
  "#22c55e",
  "#ef4444",
  "#06b6d4",
  "#ec4899",
  "#eab308",
];

/** 主图核心系列配色 */
export const NAV_LINE_COLOR = "#22c55e";
export const NAV_TREND_COLOR = "#86efac";
export const SCORE_TREND_COLOR = "#fde68a";
export const PE_LINE_COLOR = "#a78bfa";
