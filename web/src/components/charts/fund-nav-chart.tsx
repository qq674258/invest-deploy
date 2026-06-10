"use client";

import { ReactECharts } from "@/components/charts/echarts-dynamic";

type Props = {
  dates: string[];
  normalized: number[];
  nav?: number[];
};

export function FundNavChart({ dates, normalized, nav }: Props) {
  const option = {
    backgroundColor: "transparent",
    grid: { left: 52, right: 20, top: 28, bottom: 36 },
    tooltip: {
      trigger: "axis",
      formatter: (params: { dataIndex: number }[]) => {
        const i = params[0]?.dataIndex ?? 0;
        const d = dates[i];
        const n = nav?.[i];
        const pct = normalized[i];
        const lines = [d];
        if (n != null) lines.push(`净值 ${n.toFixed(4)}`);
        if (pct != null) lines.push(`业绩指数 ${pct.toFixed(2)}`);
        return lines.join("<br/>");
      },
    },
    xAxis: {
      type: "category",
      data: dates,
      axisLine: { lineStyle: { color: "#374151" } },
      axisLabel: { color: "#9ca3af", fontSize: 10 },
    },
    yAxis: {
      type: "value",
      scale: true,
      splitLine: { lineStyle: { color: "#1f2937" } },
      axisLabel: { color: "#9ca3af", fontSize: 10 },
    },
    series: [
      {
        name: "业绩走势",
        type: "line",
        data: normalized,
        smooth: true,
        symbol: "none",
        lineStyle: { color: "#10b981", width: 2 },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(16,185,129,0.22)" },
              { offset: 1, color: "rgba(16,185,129,0)" },
            ],
          },
        },
      },
    ],
  };

  return (
    <ReactECharts
      key={dates.length > 0 ? `${dates[0]}-${dates.length}` : "empty"}
      option={option}
      style={{ height: 320, width: "100%" }}
    />
  );
}
