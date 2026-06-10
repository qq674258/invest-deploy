"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { CHART_DEFAULT_LIMIT } from "@/lib/chart-range";
import { defaultQueryRetry } from "@/lib/query-utils";
import { KlineChart } from "@/components/charts/kline-chart";
import { MacroSnapshotRow } from "@/components/dashboard/macro-snapshot-row";

export function NdxHomeSection({ refreshSeq = 0 }: { refreshSeq?: number }) {
  const chart = useQuery({
    queryKey: ["market-chart", "NDX", "home", refreshSeq],
    queryFn: () => api.marketChart("NDX", CHART_DEFAULT_LIMIT, refreshSeq > 0),
    retry: defaultQueryRetry,
    refetchOnWindowFocus: true,
  });

  return (
    <section className="space-y-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted">纳斯达克100</p>
          <h2 className="mt-1 text-xl font-semibold text-foreground">走势与宏观快照</h2>
        </div>
        <Link
          href="/instruments/NDX"
          className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
        >
          详情
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      {chart.isLoading && (
        <div className="section-card h-[560px] animate-pulse bg-border/20" />
      )}

      {chart.isError && (
        <div className="alert-banner alert-banner--warning text-sm">
          纳斯达克100 走势图加载失败，请先执行 crawl。
        </div>
      )}

      {chart.data && (
        <>
          <KlineChart data={chart.data} showHeader={false} />
          <MacroSnapshotRow snapshot={chart.data.macro_snapshot} />
        </>
      )}
    </section>
  );
}
