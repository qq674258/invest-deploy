"use client";

import { useMemo, useState } from "react";
import { ReactECharts } from "@/components/charts/echarts-dynamic";
import { DrawdownHero, useDrawdownSeries } from "@/components/charts/drawdown-hero";
import type { MarketChartResponse } from "@/lib/types";
import { normalizedNavSeries, closesFromCandles } from "@/lib/chart-series";
import {
  METRIC_LABELS,
  NAV_LINE_COLOR,
  PE_LINE_COLOR,
} from "@/lib/chart-metrics";
import { CHART_DEFAULT_VISIBLE_BARS, dataZoomStartPercent } from "@/lib/chart-range";
import {
  DEFAULT_DRAWDOWN_WINDOW,
  DRAWDOWN_WINDOWS,
  type DrawdownWindowId,
} from "@/lib/drawdown";
import { useDisplaySettings } from "@/lib/display-settings";

const VIX_LINE_COLOR = "#06b6d4";

type Props = {
  data: MarketChartResponse;
  /** 是否展示标题区（首页嵌入时可关闭） */
  showHeader?: boolean;
};

export function KlineChart({ data, showHeader = true }: Props) {
  const { klineCandleStyle } = useDisplaySettings();
  const [drawdownWindow, setDrawdownWindow] =
    useState<DrawdownWindowId>(DEFAULT_DRAWDOWN_WINDOW);

  const dd = useDrawdownSeries(data.candles ?? [], drawdownWindow);
  const ddLabel = `${DRAWDOWN_WINDOWS[drawdownWindow].label}高点回撤`;

  const derived = useMemo(() => {
    const closes = closesFromCandles(data.candles ?? []);
    const nav = normalizedNavSeries(closes);
    const pe = data.indicators.pe_ttm ?? [];
    const vix = data.indicators.vix ?? [];
    const hasPe = pe.some((v) => v != null);
    const hasVix = vix.some((v) => v != null);
    return { nav, pe, vix, hasPe, hasVix };
  }, [data.candles, data.indicators]);

  const option = useMemo(() => {
    const dates = data.dates ?? [];
    const n = dates.length;
    const zoomStart = dataZoomStartPercent(CHART_DEFAULT_VISIBLE_BARS, n);

    const legendItems = ["净值走势", ddLabel];
    const legendSelected: Record<string, boolean> = {
      净值走势: true,
      [ddLabel]: true,
    };
    if (derived.hasPe) {
      legendItems.push(METRIC_LABELS.pe_ttm);
      legendSelected[METRIC_LABELS.pe_ttm] = false;
    }
    if (derived.hasVix) {
      legendItems.push(METRIC_LABELS.vix);
      legendSelected[METRIC_LABELS.vix] = false;
    }

    const yAxis: object[] = [
      {
        scale: true,
        gridIndex: 0,
        name: "净值",
        position: "left",
        axisLabel: { color: "#64748b" },
        splitLine: { lineStyle: { color: "rgba(148,163,184,0.12)" } },
      },
      {
        scale: true,
        gridIndex: 1,
        name: "回撤%",
        axisLabel: { color: "#64748b", formatter: "{value}%" },
        splitLine: { lineStyle: { color: "rgba(148,163,184,0.12)" } },
      },
    ];

    if (derived.hasPe) {
      yAxis.push({
        scale: true,
        gridIndex: 0,
        name: "PE",
        position: "right",
        axisLabel: { color: "#a78bfa" },
        splitLine: { show: false },
      });
    }
    if (derived.hasVix) {
      yAxis.push({
        scale: true,
        gridIndex: 0,
        name: "VIX",
        position: "right",
        offset: derived.hasPe ? 48 : 0,
        axisLabel: { color: "#06b6d4" },
        splitLine: { show: false },
      });
    }

    const peAxis = derived.hasPe ? 2 : -1;
    const vixAxis = derived.hasVix ? (derived.hasPe ? 3 : 2) : -1;

    const series: object[] = [
      {
        name: "净值走势",
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: derived.nav,
        showSymbol: false,
        lineStyle: { width: 2, color: NAV_LINE_COLOR },
        itemStyle: { color: NAV_LINE_COLOR },
        z: 3,
      },
      {
        name: ddLabel,
        type: "line",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: dd,
        showSymbol: false,
        lineStyle: { width: 2, color: "#f59e0b" },
        itemStyle: { color: "#f59e0b" },
        areaStyle: { color: "rgba(245,158,11,0.12)" },
      },
    ];

    if (derived.hasPe) {
      series.push({
        name: METRIC_LABELS.pe_ttm,
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: peAxis,
        data: derived.pe,
        showSymbol: false,
        lineStyle: { width: 1.5, color: PE_LINE_COLOR, type: "dashed" },
        itemStyle: { color: PE_LINE_COLOR },
        z: 2,
      });
    }
    if (derived.hasVix) {
      series.push({
        name: METRIC_LABELS.vix,
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: vixAxis,
        data: derived.vix,
        showSymbol: false,
        lineStyle: { width: 1.5, color: VIX_LINE_COLOR, type: "dashed" },
        itemStyle: { color: VIX_LINE_COLOR },
        z: 2,
      });
    }

    return {
      backgroundColor: "transparent",
      animation: false,
      tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
      legend: {
        data: legendItems,
        selected: legendSelected,
        textStyle: { color: "#94a3b8", fontSize: 11 },
        top: 0,
      },
      grid: [
        {
          left: 56,
          right:
            derived.hasPe && derived.hasVix
              ? 104
              : derived.hasPe || derived.hasVix
                ? 72
                : 56,
          top: 40,
          height: "42%",
        },
        { left: 56, right: 56, top: "58%", height: "32%" },
      ],
      xAxis: [
        { type: "category", data: dates, gridIndex: 0, axisLabel: { color: "#64748b" } },
        {
          type: "category",
          data: dates,
          gridIndex: 1,
          axisLabel: { show: false },
        },
      ],
      yAxis,
      dataZoom: [
        { type: "inside", xAxisIndex: [0, 1], start: zoomStart, end: 100 },
        {
          type: "slider",
          xAxisIndex: [0, 1],
          bottom: 4,
          height: 18,
          start: zoomStart,
          end: 100,
        },
      ],
      series,
    };
  }, [data.dates, derived, dd, ddLabel]);

  return (
    <div className="section-card space-y-4 p-4 md:p-5">
      {showHeader && (
        <div>
          <h2 className="text-lg font-semibold text-foreground">
            {data.display_name ?? data.instrument_id}
          </h2>
          <p className="mt-1 text-xs text-muted">
            默认显示近一年净值；可切换回撤窗口；点击图例叠加 PE / VIX
          </p>
        </div>
      )}

      <DrawdownHero
        candles={data.candles ?? []}
        dates={data.dates}
        windowId={drawdownWindow}
        onWindowChange={setDrawdownWindow}
      />

      <ReactECharts
        key={`${data.instrument_id}-${data.dates?.length ?? 0}-${drawdownWindow}-${klineCandleStyle}`}
        option={option}
        style={{ height: 520, width: "100%" }}
        notMerge
        lazyUpdate
      />
    </div>
  );
}
