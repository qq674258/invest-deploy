/** 走势图默认近 1 年（与后端 CHART_DEFAULT_LIMIT 一致） */
export const TRADING_DAYS_PER_YEAR = 252;
export const CHART_YEARS = 1;
export const CHART_DEFAULT_LIMIT = TRADING_DAYS_PER_YEAR * CHART_YEARS + 30;
/** K 线 / 走势图默认可见区间：近 1 年 */
export const CHART_DEFAULT_VISIBLE_BARS = TRADING_DAYS_PER_YEAR;
/** @deprecated 使用 CHART_DEFAULT_VISIBLE_BARS */
export const CHART_INITIAL_VISIBLE_BARS = CHART_DEFAULT_VISIBLE_BARS;
/** 首页评分走势图点数（近 1 年） */
export const SCORE_HISTORY_HOME_LIMIT = CHART_DEFAULT_LIMIT;

/** 侧栏分位年数 → 趋势线窗口 / 默认 dataZoom 可见 K 线根数 */
export function barsForLookbackYears(
  lookbackYears: number,
  totalBars: number
): number {
  const want = Math.max(1, lookbackYears * TRADING_DAYS_PER_YEAR);
  return Math.min(Math.max(1, totalBars), want);
}

export function dataZoomStartPercent(
  visibleBars: number,
  totalBars: number
): number {
  if (totalBars <= 1) return 0;
  return Math.max(0, 100 - (visibleBars / totalBars) * 100);
}
