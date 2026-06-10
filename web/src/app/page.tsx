"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { defaultQueryRetry, formatQueryError } from "@/lib/query-utils";
import { IndexCard } from "@/components/dashboard/score-card";
import { NdxHomeSection } from "@/components/dashboard/ndx-home-section";
import { PageHeader } from "@/components/ui/page-header";

export default function DashboardPage() {
  const [refreshSeq, setRefreshSeq] = useState(0);
  const forceRefresh = refreshSeq > 0;

  const { data, isLoading, error, isFetching, isError } = useQuery({
    queryKey: ["dashboard", refreshSeq],
    queryFn: () => api.dashboard(forceRefresh),
    retry: defaultQueryRetry,
    retryDelay: (i) => 500 * (i + 1),
    refetchOnWindowFocus: true,
  });

  return (
    <div className="w-full space-y-8">
      <PageHeader
        title="指数总览"
        description={`纳斯达克100等全球指数 · 行情最新 ${data?.as_of ?? "—"}`}
        accent="default"
        action={
          <button
            type="button"
            onClick={() => setRefreshSeq((n) => n + 1)}
            disabled={isFetching}
            className="inline-flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/10 px-4 py-2 text-sm font-medium text-primary shadow-sm shadow-primary/10 transition hover:bg-primary/15 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
            刷新
          </button>
        }
      />

      {isError && !data && !isFetching && (
        <div className="alert-banner alert-banner--danger">
          {formatQueryError(error)}
        </div>
      )}

      {isLoading && (
        <div className="grid gap-4 md:grid-cols-2">
          {[1, 2].map((i) => (
            <div
              key={i}
              className="section-card h-48 animate-pulse border-border/40 bg-border/10 !p-0"
            />
          ))}
        </div>
      )}

      {data && (
        <>
          <NdxHomeSection refreshSeq={refreshSeq} />

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {data.items
              .filter((item) => item.instrument_id !== "NDX")
              .map((item) => (
                <IndexCard key={item.instrument_id} item={item} />
              ))}
          </div>
        </>
      )}
    </div>
  );
}
