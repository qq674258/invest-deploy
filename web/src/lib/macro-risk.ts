export type RiskLevel = "low" | "moderate" | "elevated" | "high" | "unknown";

export interface RiskAssessment {
  level: RiskLevel;
  label: string;
  percent: number | null;
}

export interface MacroMetricScale {
  id: string;
  min: number;
  max: number;
  tiers: { until: number; level: RiskLevel; label: string }[];
}

const LEVEL_ORDER: RiskLevel[] = ["low", "moderate", "elevated", "high"];

export const RISK_LEVEL_COLORS: Record<
  RiskLevel,
  { bar: string; border: string; text: string; glow: string }
> = {
  low: {
    bar: "#22c55e",
    border: "border-emerald-500/45",
    text: "text-emerald-400",
    glow: "shadow-[0_0_12px_rgba(34,197,94,0.25)]",
  },
  moderate: {
    bar: "#3b82f6",
    border: "border-blue-500/45",
    text: "text-blue-400",
    glow: "shadow-[0_0_12px_rgba(59,130,246,0.2)]",
  },
  elevated: {
    bar: "#f59e0b",
    border: "border-amber-500/50",
    text: "text-amber-400",
    glow: "shadow-[0_0_12px_rgba(245,158,11,0.25)]",
  },
  high: {
    bar: "#ef4444",
    border: "border-red-500/50",
    text: "text-red-400",
    glow: "shadow-[0_0_12px_rgba(239,68,68,0.3)]",
  },
  unknown: {
    bar: "#64748b",
    border: "border-border-bright",
    text: "text-muted",
    glow: "",
  },
};

/** 参照色条：低 → 高 风险 */
export const RISK_BAR_GRADIENT =
  "linear-gradient(to right, #22c55e 0%, #3b82f6 33%, #f59e0b 66%, #ef4444 100%)";

export const METRIC_SCALES: Record<string, MacroMetricScale> = {
  pe_ttm: {
    id: "pe_ttm",
    min: 22,
    max: 42,
    tiers: [
      { until: 28, level: "low", label: "估值偏低" },
      { until: 33, level: "moderate", label: "估值中性" },
      { until: 38, level: "elevated", label: "估值偏贵" },
      { until: Infinity, level: "high", label: "估值昂贵" },
    ],
  },
  vix: {
    id: "vix",
    min: 12,
    max: 35,
    tiers: [
      { until: 15, level: "low", label: "情绪平稳" },
      { until: 20, level: "moderate", label: "波动正常" },
      { until: 28, level: "elevated", label: "恐慌升温" },
      { until: Infinity, level: "high", label: "高度恐慌" },
    ],
  },
  cpi: {
    id: "cpi",
    min: 0,
    max: 6,
    tiers: [
      { until: 2, level: "low", label: "通胀温和" },
      { until: 3, level: "moderate", label: "接近目标" },
      { until: 4, level: "elevated", label: "通胀偏高" },
      { until: Infinity, level: "high", label: "通胀压力" },
    ],
  },
  pce: {
    id: "pce",
    min: 0,
    max: 6,
    tiers: [
      { until: 2, level: "low", label: "通胀温和" },
      { until: 3, level: "moderate", label: "接近目标" },
      { until: 4, level: "elevated", label: "通胀偏高" },
      { until: Infinity, level: "high", label: "通胀压力" },
    ],
  },
};

export function assessMacroRisk(
  metricId: keyof typeof METRIC_SCALES,
  value: number | null | undefined
): RiskAssessment {
  const scale = METRIC_SCALES[metricId];
  if (value == null || !Number.isFinite(value)) {
    return { level: "unknown", label: "暂无数据", percent: null };
  }
  let level: RiskLevel = "high";
  let label = "偏高";
  for (const tier of scale.tiers) {
    if (value <= tier.until) {
      level = tier.level;
      label = tier.label;
      break;
    }
  }
  const span = scale.max - scale.min;
  const percent =
    span <= 0 ? 50 : Math.min(100, Math.max(0, ((value - scale.min) / span) * 100));
  return { level, label, percent };
}

export function riskLevelToStatTone(
  level: RiskLevel
): "success" | "primary" | "warning" | "danger" | "default" {
  switch (level) {
    case "low":
      return "success";
    case "moderate":
      return "primary";
    case "elevated":
      return "warning";
    case "high":
      return "danger";
    default:
      return "default";
  }
}

export function segmentWidths(scale: MacroMetricScale): number[] {
  const bounds = [
    scale.min,
    ...scale.tiers
      .slice(0, -1)
      .map((t) => Math.min(t.until, scale.max)),
    scale.max,
  ];
  const unique = bounds.filter(
    (v, i, arr) => i === 0 || v > arr[i - 1]
  );
  if (unique.length < 2) return [25, 25, 25, 25];
  const widths: number[] = [];
  for (let i = 1; i < unique.length; i++) {
    widths.push(((unique[i] - unique[i - 1]) / (scale.max - scale.min)) * 100);
  }
  while (widths.length < 4) widths.push(0);
  return widths.slice(0, 4);
}

export function levelColor(level: RiskLevel): string {
  return RISK_LEVEL_COLORS[level].bar;
}

export { LEVEL_ORDER };
