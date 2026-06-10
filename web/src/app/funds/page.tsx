"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { FUND_MARKETS, FUND_SECTORS } from "@/components/admin/fund-form-fields";
import { PageHeader } from "@/components/ui/page-header";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import {
  BtnPrimary,
  controlInputClass,
  controlSelectClass,
  FormLabel,
} from "@/components/ui/form-field";
import { api } from "@/lib/api";
import { defaultQueryRetry, formatQueryError } from "@/lib/query-utils";
import { cn, formatPct } from "@/lib/utils";

function returnClass(v: number | null | undefined) {
  if (v == null || !Number.isFinite(v)) return "text-muted";
  if (v > 0) return "text-emerald-400";
  if (v < 0) return "text-red-400";
  return "text-foreground";
}

function fundMetaLine(fund_manager?: string, fund_code?: string) {
  const parts = [fund_manager, fund_code].filter(Boolean);
  return parts.length > 0 ? parts.join(" - ") : null;
}

const RETURN_COLUMNS = [
  { key: "ytd" as const, label: "今年以来" },
  { key: "3m" as const, label: "近3月" },
  { key: "6m" as const, label: "近6月" },
  { key: "1y" as const, label: "近1年" },
  { key: "3y" as const, label: "近3年" },
  { key: "5y" as const, label: "近5年" },
  { key: "si" as const, label: "成立以来" },
] as const;

const stickyNameCell =
  "sticky left-0 z-10 bg-card/95 backdrop-blur-sm after:pointer-events-none after:absolute after:inset-y-0 after:right-0 after:w-px after:bg-border/40";

export default function FundsListPage() {
  const router = useRouter();
  const [searchName, setSearchName] = useState("");
  const [searchCode, setSearchCode] = useState("");
  const [searchMarket, setSearchMarket] = useState("");
  const [searchSector, setSearchSector] = useState("");
  const [applied, setApplied] = useState({
    q: "",
    code: "",
    market: "",
    sector: "",
  });

  const funds = useQuery({
    queryKey: ["fund-list", applied],
    queryFn: () =>
      api.fundList({
        q: applied.q || undefined,
        code: applied.code || undefined,
        market: applied.market || undefined,
        sector: applied.sector || undefined,
      }),
    retry: defaultQueryRetry,
  });

  const list = funds.data?.items ?? [];
  const hasFilter = useMemo(
    () => !!(applied.q || applied.code || applied.market || applied.sector),
    [applied]
  );

  function applySearch() {
    setApplied({
      q: searchName.trim(),
      code: searchCode.trim(),
      market: searchMarket,
      sector: searchSector,
    });
  }

  function resetSearch() {
    setSearchName("");
    setSearchCode("");
    setSearchMarket("");
    setSearchSector("");
    setApplied({ q: "", code: "", market: "", sector: "" });
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="我的基金"
        description="展示管理后台与各用户添加的主动基金，无需登录"
        accent="emerald"
      />

      {funds.isError && (
        <div className="alert-banner alert-banner--danger text-sm">
          {formatQueryError(funds.error)}
        </div>
      )}

      <SectionCard variant="emerald" className="space-y-4">
        <SectionCardHeader
          title="搜索"
          subtitle="支持名称/经理模糊搜索，代码精确匹配"
        />
        <div className="grid gap-3 md:grid-cols-5">
          <div className="md:col-span-2">
            <FormLabel>名称 / 经理</FormLabel>
            <div className="relative mt-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
              <input
                className={cn(controlInputClass, "pl-9")}
                value={searchName}
                onChange={(e) => setSearchName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && applySearch()}
                placeholder="基金名称、经理、板块关键字"
              />
            </div>
          </div>
          <div>
            <FormLabel>代码</FormLabel>
            <input
              className={cn(controlInputClass, "mt-1")}
              value={searchCode}
              onChange={(e) =>
                setSearchCode(e.target.value.replace(/\D/g, "").slice(0, 6))
              }
              onKeyDown={(e) => e.key === "Enter" && applySearch()}
              placeholder="6 位"
              maxLength={6}
            />
          </div>
          <div>
            <FormLabel>市场</FormLabel>
            <select
              className={cn(controlSelectClass, "mt-1")}
              value={searchMarket}
              onChange={(e) => setSearchMarket(e.target.value)}
            >
              <option value="">全部</option>
              {FUND_MARKETS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
          <div>
            <FormLabel>板块</FormLabel>
            <select
              className={cn(controlSelectClass, "mt-1")}
              value={searchSector}
              onChange={(e) => setSearchSector(e.target.value)}
            >
              <option value="">全部</option>
              {FUND_SECTORS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <BtnPrimary className="!w-auto px-6" onClick={applySearch}>
            搜索
          </BtnPrimary>
          <button
            type="button"
            className="rounded-lg border border-border px-4 py-2 text-sm text-muted hover:bg-card"
            onClick={resetSearch}
          >
            重置
          </button>
        </div>
      </SectionCard>

      <SectionCard variant="muted" padding={false}>
        <SectionCardHeader
          title="基金列表"
          subtitle={`共 ${funds.data?.total ?? (funds.isLoading ? "—" : 0)} 只${hasFilter ? "（已筛选）" : ""}`}
        />

        {funds.isLoading && (
          <p className="px-4 py-10 text-center text-sm text-muted">加载中…</p>
        )}

        {!funds.isLoading && list.length === 0 && (
          <p className="px-4 py-10 text-center text-sm text-muted">
            {hasFilter
              ? "无匹配基金，请调整搜索条件"
              : "暂无基金，请在管理后台录入或由用户添加后同步展示"}
          </p>
        )}

        {!funds.isLoading && list.length > 0 && (
          <div className="-mx-1 overflow-x-auto px-1 pb-1">
            <table className="data-table w-full min-w-[1100px] text-sm">
              <thead>
                <tr className="text-left text-xs text-muted">
                  <th className={cn("min-w-[168px] px-4 py-2", stickyNameCell)}>名称</th>
                  {RETURN_COLUMNS.map((col) => (
                    <th key={col.key} className="whitespace-nowrap px-3 py-2 text-right">
                      {col.label}
                    </th>
                  ))}
                  <th className="whitespace-nowrap px-4 py-2">数据</th>
                </tr>
              </thead>
              <tbody>
                {list.map((f) => {
                  const meta = fundMetaLine(f.fund_manager, f.fund_code);
                  const href = `/funds/${f.instrument_id}`;
                  return (
                    <tr
                      key={f.instrument_id}
                      role="link"
                      tabIndex={0}
                      onClick={() => router.push(href)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          router.push(href);
                        }
                      }}
                      className="group cursor-pointer border-t border-border/30 transition hover:bg-emerald-500/5"
                    >
                      <td className={cn("px-4 py-2.5 group-hover:bg-emerald-500/5", stickyNameCell)}>
                        <Link
                          href={href}
                          className="font-medium text-foreground hover:text-emerald-400"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {f.display_name}
                        </Link>
                        {meta && (
                          <p className="text-[10px] text-muted">{meta}</p>
                        )}
                      </td>
                      {RETURN_COLUMNS.map((col) => (
                        <td
                          key={col.key}
                          className={cn(
                            "whitespace-nowrap px-3 py-2.5 text-right tabular-nums font-medium",
                            returnClass(f.returns[col.key])
                          )}
                        >
                          {formatPct(f.returns[col.key])}
                        </td>
                      ))}
                      <td className="whitespace-nowrap px-4 py-2.5 text-xs tabular-nums text-muted">
                        {f.nav_rows > 0 ? (
                          <>
                            {f.nav_rows} 条 · {f.latest_nav_date ?? "—"}
                          </>
                        ) : (
                          "未采集"
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>
    </div>
  );
}
