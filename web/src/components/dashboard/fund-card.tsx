"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { DashboardItem } from "@/lib/types";
import { cn, formatPct } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

export function FundCard({ item }: { item: DashboardItem }) {
  const daily = item.latest_daily_return_pct;

  return (
    <Link
      href={`/funds/${item.instrument_id}`}
      className={cn(
        "section-card group block border-border/60 bg-gradient-to-br from-card/95 to-card/70 p-5 transition-all",
        "hover:-translate-y-0.5 hover:border-emerald-500/45 hover:shadow-card-primary"
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted">
            {item.fund_code ?? item.instrument_id}
            {item.sector ? ` · ${item.sector}` : item.market ? ` · ${item.market}` : " · 基金"}
          </p>
          <h3 className="mt-1 text-lg font-semibold text-foreground">
            {item.display_name}
          </h3>
        </div>
        <ArrowRight className="h-4 w-4 text-emerald-400 opacity-0 transition group-hover:opacity-100" />
      </div>

      <div className="mt-6">
        <div className="inline-block rounded-xl border border-emerald-500/25 bg-emerald-500/5 px-4 py-3">
          <p className="text-xs text-muted">最新净值</p>
          <p className="mt-1 text-3xl font-bold tabular-nums text-foreground">
            {item.latest_nav != null ? item.latest_nav.toFixed(4) : "—"}
          </p>
          {daily != null && (
            <Badge
              className={cn(
                "mt-2 border-current/20",
                daily >= 0 ? "text-emerald-400" : "text-red-400"
              )}
            >
              {formatPct(daily)}
            </Badge>
          )}
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-border/40 pt-3 text-[11px] text-muted">
        <span>数据 {item.data?.last_date ?? "—"}</span>
        <span>{item.fund_manager ?? "查看详情"}</span>
      </div>
    </Link>
  );
}
