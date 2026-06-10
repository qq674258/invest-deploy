"use client";

import type { MacroSnapshot, MacroSnapshotPoint } from "@/lib/types";
import { MacroRiskMeter } from "@/components/dashboard/macro-risk-meter";
import { StatBox } from "@/components/ui/stat-box";
import {
  assessMacroRisk,
  METRIC_SCALES,
  RISK_LEVEL_COLORS,
  riskLevelToStatTone,
} from "@/lib/macro-risk";
import { cn } from "@/lib/utils";

const RISK_NOTES = {
  pe_ttm: "PE 越高通常估值越贵，长期回报空间往往收窄，高位追涨风险偏大",
  vix: "VIX 越高市场恐慌与波动越大，短期不确定性上升",
  cpi: "CPI 同比越高通胀压力越大，利率偏紧时风险资产往往承压",
  pce: "PCE 同比越高通胀黏性越强，美联储偏紧预期升温时风险偏高",
} as const;

type MetricKey = keyof typeof RISK_NOTES;

function fmtValue(
  pt: { value?: number | null; unit?: string | null } | undefined,
  digits = 2
): string {
  if (pt?.value == null || !Number.isFinite(pt.value)) return "—";
  const unit = pt.unit ?? "";
  if (unit === "%") return `${pt.value.toFixed(digits)}%`;
  if (unit === "×") return `${pt.value.toFixed(digits)}×`;
  return pt.value.toFixed(digits);
}

function fmtDateLine(pt: MacroSnapshotPoint | undefined): string | undefined {
  if (!pt?.date) return pt?.label ?? undefined;
  return pt.label ? `${pt.label} · ${pt.date}` : pt.date;
}

function MacroHint({
  pt,
  riskNote,
  fallbackDate,
}: {
  pt?: MacroSnapshotPoint;
  riskNote: string;
  fallbackDate?: string;
}) {
  const dateLine = fmtDateLine(pt) ?? fallbackDate;
  return (
    <span className="block space-y-1">
      {dateLine && <span className="block">{dateLine}</span>}
      <span className="block text-[10px] leading-snug text-muted/85">{riskNote}</span>
    </span>
  );
}

function MacroMetricCard({
  metricId,
  label,
  pt,
  riskNote,
  fallbackDate,
  valueDigits = 2,
}: {
  metricId: MetricKey;
  label: string;
  pt?: MacroSnapshotPoint;
  riskNote: string;
  fallbackDate?: string;
  valueDigits?: number;
}) {
  const scale = METRIC_SCALES[metricId];
  const assessment = assessMacroRisk(metricId, pt?.value);
  const colors = RISK_LEVEL_COLORS[assessment.level];

  return (
    <div className="space-y-2">
      <MacroRiskMeter scale={scale} assessment={assessment} />
      <StatBox
        label={label}
        value={
          <span className={cn("tabular-nums", colors.text)}>
            {fmtValue(pt, valueDigits)}
          </span>
        }
        hint={
          <MacroHint pt={pt} riskNote={riskNote} fallbackDate={fallbackDate} />
        }
        tone={riskLevelToStatTone(assessment.level)}
        className={cn(colors.glow, colors.border)}
        valueClassName={colors.text}
      />
    </div>
  );
}

export function MacroSnapshotRow({ snapshot }: { snapshot?: MacroSnapshot }) {
  if (!snapshot) return null;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <MacroMetricCard
        metricId="pe_ttm"
        label="PE (TTM)"
        pt={snapshot.pe_ttm}
        riskNote={RISK_NOTES.pe_ttm}
      />
      <MacroMetricCard
        metricId="vix"
        label="VIX"
        pt={snapshot.vix}
        riskNote={RISK_NOTES.vix}
        valueDigits={2}
      />
      <MacroMetricCard
        metricId="cpi"
        label="美国 CPI"
        pt={snapshot.cpi}
        riskNote={RISK_NOTES.cpi}
        fallbackDate="同比通胀"
      />
      <MacroMetricCard
        metricId="pce"
        label="PCE"
        pt={snapshot.pce}
        riskNote={RISK_NOTES.pce}
        fallbackDate="同比通胀"
      />
    </div>
  );
}
