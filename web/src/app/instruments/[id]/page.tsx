"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { api } from "@/lib/api";
import { CHART_DEFAULT_LIMIT } from "@/lib/chart-range";
import { KlineChart } from "@/components/charts/kline-chart";
import { PageHeader } from "@/components/ui/page-header";
import { formatQueryError } from "@/lib/query-utils";

export default function InstrumentDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const chart = useQuery({
    queryKey: ["market-chart", id],
    queryFn: () => api.marketChart(id, CHART_DEFAULT_LIMIT),
  });

  return (
    <div className="relative w-full space-y-5">
      <Link
        href="/"
        className="inline-flex items-center gap-1 text-sm text-muted hover:text-foreground"
      >
        <ChevronLeft className="h-4 w-4" />
        返回总览
      </Link>

      <PageHeader
        title={chart.data?.display_name ?? id}
        description={`${id} · 走势与高点回撤`}
        accent="default"
      />

      {chart.isLoading && (
        <div className="section-card h-96 animate-pulse bg-border/20" />
      )}

      {chart.data && <KlineChart data={chart.data} />}

      {chart.isError && !chart.isFetching && (
        <div className="alert-banner alert-banner--danger text-sm">
          {formatQueryError(chart.error) || "加载行情失败，请先在管理后台执行 crawl。"}
        </div>
      )}
    </div>
  );
}
