"use client";

import type { AllInSignalTier } from "@/lib/types";
import { cn } from "@/lib/utils";

const TIER_STYLES: Record<string, string> = {
  very_cheap: "border-success/50 bg-success/10 text-success",
  cheap: "border-emerald-400/40 bg-emerald-500/10 text-emerald-300",
  fair: "border-warning/45 bg-warning/10 text-warning",
  expensive: "border-orange-400/40 bg-orange-500/10 text-orange-300",
  very_expensive: "border-danger/50 bg-danger/10 text-danger",
  shallow: "border-slate-400/40 bg-slate-500/10 text-slate-200",
  mild: "border-sky-400/40 bg-sky-500/10 text-sky-200",
  moderate: "border-warning/45 bg-warning/10 text-warning",
  deep: "border-emerald-400/40 bg-emerald-500/10 text-emerald-300",
  extreme: "border-danger/50 bg-danger/10 text-danger",
  low: "border-slate-400/40 bg-slate-500/10 text-slate-200",
  normal: "border-sky-400/40 bg-sky-500/10 text-sky-200",
  elevated: "border-warning/45 bg-warning/10 text-warning",
  high: "border-emerald-400/40 bg-emerald-500/10 text-emerald-300",
  weak: "border-danger/50 bg-danger/10 text-danger",
  mild_growth: "border-orange-400/40 bg-orange-500/10 text-orange-300",
  healthy: "border-emerald-400/40 bg-emerald-500/10 text-emerald-300",
  strong: "border-success/50 bg-success/10 text-success",
  very_strong: "border-violet-400/40 bg-violet-500/10 text-violet-200",
};

export function SignalTierTable({
  title,
  subtitle,
  tiers,
  activeTierId,
  currentValue,
  currentLabel,
  valueSuffix = "",
}: {
  title: string;
  subtitle?: string;
  tiers: AllInSignalTier[];
  activeTierId?: string | null;
  currentValue?: string | null;
  currentLabel?: string | null;
  valueSuffix?: string;
}) {
  if (!tiers.length) return null;

  return (
    <div className="space-y-3">
      <div>
        <h4 className="text-sm font-semibold text-foreground">{title}</h4>
        {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
      </div>
      <div className="overflow-x-auto rounded-lg border border-border-bright">
        <table className="data-table w-full min-w-[640px] text-sm">
          <thead>
            <tr className="text-left text-xs text-muted">
              <th className="px-3 py-2.5 font-medium">档位</th>
              <th className="px-3 py-2.5 font-medium">区间</th>
              <th className="px-3 py-2.5 font-medium">All in 建议</th>
            </tr>
          </thead>
          <tbody>
            {tiers.map((tier) => {
              const active = tier.id === activeTierId;
              return (
                <tr
                  key={tier.id}
                  className={cn(
                    "border-t border-border/40",
                    active && "bg-primary/[0.08] ring-1 ring-inset ring-primary/30"
                  )}
                >
                  <td className="px-3 py-2.5">
                    <span
                      className={cn(
                        "inline-flex rounded-md border px-2 py-0.5 text-xs font-semibold",
                        TIER_STYLES[tier.id] ?? "border-border-bright text-foreground"
                      )}
                    >
                      {tier.label}
                      {active && (
                        <span className="ml-1.5 text-[10px] font-normal opacity-80">
                          ← 当前
                        </span>
                      )}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 tabular-nums text-muted">{tier.range}</td>
                  <td className="px-3 py-2.5 text-xs leading-relaxed text-muted">
                    {tier.advice}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {currentValue != null && (
        <p className="text-xs text-muted">
          买入日当前值{" "}
          <strong className="text-foreground">
            {currentValue}
            {valueSuffix}
          </strong>
          {currentLabel && (
            <>
              {" "}
              · 档位 <strong className="text-foreground">{currentLabel}</strong>
            </>
          )}
        </p>
      )}
    </div>
  );
}
