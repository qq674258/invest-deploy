"use client";

import { cn } from "@/lib/utils";
import {
  LEVEL_ORDER,
  RISK_BAR_GRADIENT,
  RISK_LEVEL_COLORS,
  type MacroMetricScale,
  type RiskAssessment,
} from "@/lib/macro-risk";

const SEGMENT_COLORS = LEVEL_ORDER.map((l) => RISK_LEVEL_COLORS[l].bar);

type Props = {
  scale: MacroMetricScale;
  assessment: RiskAssessment;
  className?: string;
};

export function MacroRiskMeter({ scale, assessment, className }: Props) {
  const colors = RISK_LEVEL_COLORS[assessment.level];
  const markerLeft =
    assessment.percent != null ? `${assessment.percent}%` : "50%";

  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-center justify-between gap-2 text-[9px] text-muted">
        <span>低风险</span>
        <span
          className={cn(
            "rounded px-1.5 py-0.5 font-medium tabular-nums",
            colors.text,
            assessment.level !== "unknown" && "bg-white/5"
          )}
        >
          {assessment.label}
        </span>
        <span>高风险</span>
      </div>

      <div className="relative px-0.5 pt-1">
        <div
          className="relative h-2 overflow-hidden rounded-full ring-1 ring-white/10"
          style={{ background: RISK_BAR_GRADIENT }}
          title={`${scale.min} → ${scale.max}`}
        />
        {assessment.percent != null && (
          <div
            className="pointer-events-none absolute top-0 flex -translate-x-1/2 flex-col items-center"
            style={{ left: markerLeft }}
          >
            <div
              className="h-0 w-0 border-x-[5px] border-b-[6px] border-x-transparent"
              style={{ borderBottomColor: colors.bar }}
            />
            <div
              className="h-3 w-1 rounded-full"
              style={{
                backgroundColor: colors.bar,
                boxShadow: `0 0 8px ${colors.bar}`,
              }}
            />
          </div>
        )}
      </div>

      <div className="flex h-1 overflow-hidden rounded-full opacity-60">
        {SEGMENT_COLORS.map((c, i) => (
          <div
            key={i}
            className="h-full flex-1 first:rounded-l-full last:rounded-r-full"
            style={{ backgroundColor: c }}
          />
        ))}
      </div>
    </div>
  );
}
