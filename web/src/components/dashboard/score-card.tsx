"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { DashboardItem } from "@/lib/types";
import { cn } from "@/lib/utils";

export function IndexCard({ item }: { item: DashboardItem }) {
  const isFund = item.asset_class === "cn_active_fund";

  return (
    <Link
      href={isFund ? `/funds/${item.instrument_id}` : `/instruments/${item.instrument_id}`}
      className={cn(
        "section-card group block border-border/60 bg-gradient-to-br from-card/95 to-card/70 p-5 transition-all hover:-translate-y-0.5 hover:shadow-card-primary",
        isFund ? "hover:border-emerald-500/45" : "hover:border-primary/45"
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted">
            {isFund
              ? `${item.fund_code ?? item.instrument_id} · ${item.market ?? "基金"}`
              : item.instrument_id}
          </p>
          <h3 className="mt-1 text-lg font-semibold text-foreground">{item.display_name}</h3>
        </div>
        <ArrowRight className="h-4 w-4 text-primary opacity-0 transition group-hover:opacity-100" />
      </div>

      <p className="mt-6 text-sm text-muted">
        {isFund ? "查看基金净值与持仓" : "查看走势与近半年高点回撤"}
      </p>

      <div className="mt-4 flex items-center justify-between border-t border-border/40 pt-3 text-[11px] text-muted">
        <span>数据 {item.data?.last_date ?? "—"}</span>
        <span>{item.data?.rows != null ? `${item.data.rows} 条` : ""}</span>
      </div>
    </Link>
  );
}
