"use client";

import dynamic from "next/dynamic";
import type { ComponentProps } from "react";
import { ChartErrorBoundary } from "@/components/charts/chart-error-boundary";

const EChartsCore = dynamic(() => import("@/components/charts/echarts-bundle"), {
  ssr: false,
  loading: () => (
    <div className="flex min-h-[200px] items-center justify-center text-xs text-muted">
      图表加载中…
    </div>
  ),
});

type EChartsProps = ComponentProps<typeof EChartsCore>;

function chartMinHeight(style?: EChartsProps["style"]): number {
  if (!style || typeof style !== "object" || !("height" in style)) return 200;
  const h = style.height;
  return typeof h === "number" ? h : 200;
}

export function ReactECharts(props: EChartsProps) {
  return (
    <ChartErrorBoundary minHeight={chartMinHeight(props.style)}>
      <EChartsCore {...props} />
    </ChartErrorBoundary>
  );
}
