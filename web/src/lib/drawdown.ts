/** 滚动高点回撤窗口（交易日） */
export type DrawdownWindowId = "1m" | "3m" | "6m" | "1y";

export const DRAWDOWN_WINDOWS: Record<
  DrawdownWindowId,
  { days: number; label: string; shortLabel: string }
> = {
  "1m": { days: 21, label: "近1月", shortLabel: "1月" },
  "3m": { days: 63, label: "近3月", shortLabel: "3月" },
  "6m": { days: 126, label: "近6月", shortLabel: "6月" },
  "1y": { days: 252, label: "近1年", shortLabel: "1年" },
};

export const DEFAULT_DRAWDOWN_WINDOW: DrawdownWindowId = "1m";

/** 收盘价序列 → 相对滚动高点的回撤 %（≤0） */
export function rollingDrawdownPct(
  closes: (number | null)[],
  lookbackDays: number
): (number | null)[] {
  const lb = Math.max(1, lookbackDays);
  const minPeriods = Math.min(lb, 20);
  const out: (number | null)[] = [];

  for (let i = 0; i < closes.length; i++) {
    const start = Math.max(0, i - lb + 1);
    const windowLen = i - start + 1;
    if (windowLen < minPeriods) {
      out.push(null);
      continue;
    }
    let rollMax = -Infinity;
    let has = false;
    for (let j = start; j <= i; j++) {
      const c = closes[j];
      if (c != null && c > 0) {
        rollMax = Math.max(rollMax, c);
        has = true;
      }
    }
    const cur = closes[i];
    if (!has || cur == null || cur <= 0 || rollMax <= 0) {
      out.push(null);
    } else {
      out.push(((cur / rollMax) - 1) * 100);
    }
  }
  return out;
}

export function latestDrawdown(
  series: (number | null)[]
): number | null {
  for (let i = series.length - 1; i >= 0; i--) {
    const v = series[i];
    if (v != null && Number.isFinite(v)) return v;
  }
  return null;
}

export function matchDrawdownTier(ddPct: number): {
  id: string;
  label: string;
} {
  const dd = ddPct / 100;
  if (dd > -0.05) return { id: "shallow", label: "轻微回撤" };
  if (dd > -0.1) return { id: "mild", label: "轻度回撤" };
  if (dd > -0.2) return { id: "moderate", label: "中度回撤" };
  if (dd > -0.35) return { id: "deep", label: "深度回撤" };
  return { id: "extreme", label: "极端回撤" };
}

export function drawdownDisplayTone(
  ddPct: number | null
): "success" | "primary" | "warning" | "danger" | "muted" {
  if (ddPct == null) return "muted";
  const { label } = matchDrawdownTier(ddPct);
  if (label.includes("深度") || label.includes("极端")) return "success";
  if (label.includes("中度")) return "primary";
  if (label.includes("轻微")) return "danger";
  return "warning";
}
