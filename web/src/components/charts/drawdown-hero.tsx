"use client";

import {
  DEFAULT_DRAWDOWN_WINDOW,
  DRAWDOWN_WINDOWS,
  drawdownDisplayTone,
  latestDrawdown,
  matchDrawdownTier,
  rollingDrawdownPct,
  type DrawdownWindowId,
} from "@/lib/drawdown";
import { closesFromCandles } from "@/lib/chart-series";
import { SegmentButton } from "@/components/ui/form-field";
import { cn, formatPct } from "@/lib/utils";
import { useMemo, useState } from "react";

const TONE_CLASS = {
  success: "border-emerald-500/50 bg-emerald-500/10 text-emerald-400",
  primary: "border-primary/50 bg-primary/10 text-primary",
  warning: "border-amber-500/50 bg-amber-500/10 text-amber-400",
  danger: "border-red-500/50 bg-red-500/10 text-red-400",
  muted: "border-border/50 bg-card/40 text-muted",
} as const;

type Props = {
  candles: number[][];
  dates?: string[];
  /** 受控窗口；不传则组件内部管理，默认 1 月 */
  windowId?: DrawdownWindowId;
  onWindowChange?: (id: DrawdownWindowId) => void;
  className?: string;
};

export function DrawdownHero({
  candles,
  dates,
  windowId: controlledWindow,
  onWindowChange,
  className,
}: Props) {
  const [internalWindow, setInternalWindow] =
    useState<DrawdownWindowId>(DEFAULT_DRAWDOWN_WINDOW);
  const windowId = controlledWindow ?? internalWindow;

  const setWindow = (id: DrawdownWindowId) => {
    if (onWindowChange) onWindowChange(id);
    else setInternalWindow(id);
  };

  const { latest, tier, windowMeta, lastDate } = useMemo(() => {
    const closes = closesFromCandles(candles);
    const meta = DRAWDOWN_WINDOWS[windowId];
    const series = rollingDrawdownPct(closes, meta.days);
    const latestVal = latestDrawdown(series);
    const tierInfo =
      latestVal != null ? matchDrawdownTier(latestVal) : { id: "", label: "—" };
    const lastDate =
      dates && dates.length > 0 ? dates[dates.length - 1] : undefined;
    return {
      latest: latestVal,
      tier: tierInfo,
      windowMeta: meta,
      lastDate,
    };
  }, [candles, dates, windowId]);

  const tone = drawdownDisplayTone(latest);

  return (
    <div
      className={cn(
        "rounded-xl border p-4 md:p-5",
        TONE_CLASS[tone],
        className
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider opacity-80">
            高点回撤
          </p>
          <p className="mt-1 text-4xl font-bold tabular-nums tracking-tight md:text-5xl">
            {latest != null ? formatPct(latest) : "—"}
          </p>
          <p className="mt-2 text-sm opacity-90">
            {tier.label}
            <span className="mx-1.5 opacity-50">·</span>
            相对{windowMeta.label}滚动最高价
            {lastDate && (
              <>
                <span className="mx-1.5 opacity-50">·</span>
                {lastDate}
              </>
            )}
          </p>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {(Object.keys(DRAWDOWN_WINDOWS) as DrawdownWindowId[]).map((id) => (
            <SegmentButton
              key={id}
              active={windowId === id}
              onClick={() => setWindow(id)}
              className="min-w-[3rem] px-3 py-1.5 text-xs"
            >
              {DRAWDOWN_WINDOWS[id].shortLabel}
            </SegmentButton>
          ))}
        </div>
      </div>
    </div>
  );
}

/** 供 K 线图同步使用的回撤序列 */
export function useDrawdownSeries(
  candles: number[][],
  windowId: DrawdownWindowId
): (number | null)[] {
  return useMemo(() => {
    const closes = closesFromCandles(candles);
    return rollingDrawdownPct(closes, DRAWDOWN_WINDOWS[windowId].days);
  }, [candles, windowId]);
}
