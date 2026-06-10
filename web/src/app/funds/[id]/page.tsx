"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { ChevronLeft } from "lucide-react";
import { FundNavChart } from "@/components/charts/fund-nav-chart";
import { Badge } from "@/components/ui/badge";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { CHART_DEFAULT_LIMIT } from "@/lib/chart-range";
import { api } from "@/lib/api";
import { defaultQueryRetry, formatQueryError } from "@/lib/query-utils";
import type { FundPeriodReturn } from "@/lib/types";
import { cn, formatPct } from "@/lib/utils";

const TABS = [
  { id: "performance", label: "业绩走势" },
  { id: "history", label: "历史业绩" },
  { id: "nav", label: "历史净值" },
  { id: "holdings", label: "持仓" },
  { id: "managers", label: "基金经理" },
  { id: "rules", label: "交易规则" },
] as const;

type TabId = (typeof TABS)[number]["id"];

function returnColor(v: number | null | undefined) {
  if (v == null || !Number.isFinite(v)) return "text-muted";
  if (v > 0) return "text-emerald-400";
  if (v < 0) return "text-red-400";
  return "text-foreground";
}

function PeriodTable({
  title,
  rows,
  showPeer = false,
}: {
  title: string;
  rows: FundPeriodReturn[];
  showPeer?: boolean;
}) {
  if (!rows.length) {
    return <p className="py-6 text-center text-sm text-muted">暂无数据</p>;
  }
  return (
    <div>
      <p className="mb-3 text-xs text-muted">{title}</p>
      <div className="overflow-x-auto">
        <table className="data-table w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-muted">
              <th className="pb-2 pr-4">区间</th>
              <th className="pb-2 pr-4">涨跌幅</th>
              {showPeer && (
                <>
                  <th className="pb-2 pr-4">同类平均</th>
                  <th className="pb-2 pr-4">沪深300</th>
                  <th className="pb-2">排名</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.period_id + r.label} className="border-t border-border/30">
                <td className="py-2.5 pr-4 text-foreground">{r.label}</td>
                <td
                  className={cn(
                    "py-2.5 pr-4 font-medium tabular-nums",
                    returnColor(r.return_pct)
                  )}
                >
                  {formatPct(r.return_pct)}
                </td>
                {showPeer && (
                  <>
                    <td className="py-2.5 pr-4 tabular-nums text-muted">
                      {formatPct(r.peer_avg_pct)}
                    </td>
                    <td className="py-2.5 pr-4 tabular-nums text-muted">
                      {formatPct(r.benchmark_pct)}
                    </td>
                    <td className="py-2.5 text-xs text-muted">
                      {r.rank && r.peer_count
                        ? `${r.rank}/${r.peer_count}`
                        : r.rank ?? "—"}
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function FundDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const id = params.id as string;
  const initialTab = (searchParams.get("tab") as TabId) || "performance";
  const [tab, setTab] = useState<TabId>(
    TABS.some((t) => t.id === initialTab) ? initialTab : "performance"
  );
  const [navPage, setNavPage] = useState(0);
  const navLimit = 20;

  const queryOpts = {
    retry: defaultQueryRetry,
    retryDelay: (i: number) => 500 * (i + 1),
  };

  const summary = useQuery({
    queryKey: ["fund-summary", id],
    queryFn: () => api.fundSummary(id),
    ...queryOpts,
  });

  const performance = useQuery({
    queryKey: ["fund-performance", id],
    queryFn: () => api.fundPerformance(id, CHART_DEFAULT_LIMIT),
    enabled: tab === "performance" || tab === "history",
    ...queryOpts,
  });

  const nav = useQuery({
    queryKey: ["fund-nav", id, navPage],
    queryFn: () => api.fundNav(id, navLimit, navPage * navLimit),
    enabled: tab === "nav",
  });

  const holdings = useQuery({
    queryKey: ["fund-holdings", id],
    queryFn: () => api.fundHoldings(id),
    enabled: tab === "holdings",
  });

  const managers = useQuery({
    queryKey: ["fund-managers", id],
    queryFn: () => api.fundManagers(id),
    enabled: tab === "managers",
  });

  const rules = useQuery({
    queryKey: ["fund-rules", id],
    queryFn: () => api.fundTradingRules(id),
    enabled: tab === "rules",
  });

  const s = summary.data;
  const daily = s?.daily_return_pct;

  const officialPeriods = performance.data?.official_periods ?? [];
  const computedPeriods =
    performance.data?.computed_periods ?? s?.period_returns ?? [];

  const rulesData = useMemo(() => {
    const r = rules.data?.rules ?? s?.trading_rules;
    if (!r || typeof r !== "object") return [];
    const labels: Record<string, string> = {
      purchase_status: "申购状态",
      redeem_status: "赎回状态",
      min_purchase: "起购金额",
      management_fee: "管理费",
      custody_fee: "托管费",
      sales_fee: "销售服务费",
      performance_benchmark: "业绩比较基准",
      subscription_fee: "申购费率",
      redemption_fee: "赎回费率",
      dca_supported: "定投",
      trade_notes: "说明",
    };
    return Object.entries(labels)
      .map(([key, label]) => ({
        label,
        value: (r as Record<string, unknown>)[key],
      }))
      .filter((x) => x.value != null && x.value !== "" && x.value !== "--");
  }, [rules.data, s?.trading_rules]);

  return (
    <div className="w-full space-y-6 pb-10">
      <Link
        href="/funds"
        className="inline-flex items-center gap-1 text-sm text-muted hover:text-primary"
      >
        <ChevronLeft className="h-4 w-4" />
        返回基金列表
      </Link>

      {summary.isLoading && (
        <div className="section-card h-40 animate-pulse bg-border/10" />
      )}

      {summary.isError && !summary.data && !summary.isFetching && (
        <div className="alert-banner alert-banner--danger text-sm">
          加载失败：{formatQueryError(summary.error)}
        </div>
      )}

      {s && (
        <SectionCard variant="emerald" className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs text-muted">
                {s.fund_code}
                {s.sector ? ` · ${s.sector}` : s.market ? ` · ${s.market}` : " · 基金"}
                {s.fund_type ? ` · ${s.fund_type}` : ""}
              </p>
              <h1 className="mt-1 text-2xl font-semibold tracking-tight">
                {s.display_name}
              </h1>
              <p className="mt-2 text-sm text-muted">
                {s.fund_company ?? "—"}
                {s.fund_manager ? ` · ${s.fund_manager}` : ""}
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-muted">最新净值</p>
              <p className="text-3xl font-bold tabular-nums text-foreground">
                {s.latest_nav != null ? s.latest_nav.toFixed(4) : "—"}
              </p>
              <p className="mt-1 text-xs text-muted">{s.latest_nav_date ?? "—"}</p>
              {daily != null && (
                <Badge
                  className={cn(
                    "mt-2 border-current/20",
                    daily >= 0 ? "text-emerald-400" : "text-red-400"
                  )}
                >
                  {daily >= 0 ? "+" : ""}
                  {daily.toFixed(2)}%
                </Badge>
              )}
            </div>
          </div>
        </SectionCard>
      )}

      <div className="flex gap-1 overflow-x-auto border-b border-border/50 pb-px">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={cn(
              "shrink-0 rounded-t-lg px-4 py-2.5 text-sm transition",
              tab === t.id
                ? "border border-b-0 border-emerald-500/40 bg-emerald-500/10 font-medium text-emerald-400"
                : "text-muted hover:bg-card/60 hover:text-foreground"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "performance" && (
        <SectionCard>
          <SectionCardHeader
            title="业绩走势"
            subtitle="以区间起点净值为 100 的归一化曲线（类似支付宝业绩走势）"
          />
          {performance.isLoading && (
            <div className="h-80 animate-pulse rounded-lg bg-border/10" />
          )}
          {performance.data?.chart?.dates?.length ? (
            <FundNavChart
              dates={performance.data.chart.dates}
              normalized={performance.data.chart.normalized}
              nav={performance.data.chart.nav}
            />
          ) : (
            !performance.isLoading && (
              <p className="py-12 text-center text-sm text-muted">
                暂无净值，请先在管理后台爬取数据
              </p>
            )
          )}
          {computedPeriods.length > 0 && (
            <div className="mt-6 border-t border-border/40 pt-6">
              <PeriodTable title="根据本地净值计算的区间收益" rows={computedPeriods} />
            </div>
          )}
        </SectionCard>
      )}

      {tab === "history" && (
        <SectionCard>
          <SectionCardHeader
            title="历史业绩"
            subtitle="东财阶段涨幅；含同类与沪深300对比（如有）"
          />
          {performance.isLoading && (
            <div className="h-48 animate-pulse rounded-lg bg-border/10" />
          )}
          <PeriodTable
            title="官方阶段涨幅"
            rows={officialPeriods}
            showPeer
          />
          {!performance.isLoading && !officialPeriods.length && (
            <PeriodTable title="本地计算（备用）" rows={computedPeriods} />
          )}
        </SectionCard>
      )}

      {tab === "nav" && (
        <SectionCard padding={false}>
          <SectionCardHeader
            title="历史净值"
            subtitle={nav.data ? `共 ${nav.data.total} 条` : ""}
            className="px-4 pt-4"
          />
          {nav.isLoading && (
            <p className="px-4 py-8 text-center text-sm text-muted">加载中…</p>
          )}
          {nav.data && (
            <>
              <div className="overflow-x-auto">
                <table className="data-table w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-muted">
                      <th className="px-4 py-2">日期</th>
                      <th className="px-4 py-2">单位净值</th>
                      <th className="px-4 py-2">累计净值</th>
                      <th className="px-4 py-2">日涨跌</th>
                    </tr>
                  </thead>
                  <tbody>
                    {nav.data.rows.map((r) => (
                      <tr key={r.nav_date} className="border-t border-border/30">
                        <td className="px-4 py-2 tabular-nums">{r.nav_date}</td>
                        <td className="px-4 py-2 tabular-nums">{r.nav.toFixed(4)}</td>
                        <td className="px-4 py-2 tabular-nums text-muted">
                          {r.acc_nav != null ? r.acc_nav.toFixed(4) : "—"}
                        </td>
                        <td
                          className={cn(
                            "px-4 py-2 tabular-nums",
                            returnColor(
                              r.daily_return != null ? r.daily_return * 100 : null
                            )
                          )}
                        >
                          {r.daily_return != null
                            ? `${r.daily_return >= 0 ? "+" : ""}${(r.daily_return * 100).toFixed(2)}%`
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between border-t border-border/40 px-4 py-3">
                <button
                  type="button"
                  disabled={navPage === 0}
                  className="rounded border border-border px-3 py-1 text-xs disabled:opacity-40"
                  onClick={() => setNavPage((p) => Math.max(0, p - 1))}
                >
                  上一页
                </button>
                <span className="text-xs text-muted">第 {navPage + 1} 页</span>
                <button
                  type="button"
                  disabled={(navPage + 1) * navLimit >= (nav.data?.total ?? 0)}
                  className="rounded border border-border px-3 py-1 text-xs disabled:opacity-40"
                  onClick={() => setNavPage((p) => p + 1)}
                >
                  下一页
                </button>
              </div>
            </>
          )}
        </SectionCard>
      )}

      {tab === "holdings" && (
        <SectionCard padding={false}>
          <SectionCardHeader
            title="基金持仓"
            subtitle={
              holdings.data?.report_date
                ? `报告期 ${holdings.data.report_date} · ${holdings.data.disclaimer ?? ""}`
                : "季报披露，存在滞后"
            }
            className="px-4 pt-4"
          />
          {holdings.isLoading && (
            <p className="px-4 py-8 text-center text-sm text-muted">加载中…</p>
          )}
          {holdings.data && !holdings.data.holdings.length && (
            <p className="px-4 py-8 text-center text-sm text-muted">
              暂无持仓数据，请重新爬取或该基金可能无股票重仓披露
            </p>
          )}
          {holdings.data && holdings.data.holdings.length > 0 && (
            <div className="overflow-x-auto">
              <table className="data-table w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-muted">
                    <th className="px-4 py-2">名称</th>
                    <th className="px-4 py-2">代码</th>
                    <th className="px-4 py-2">占净值比</th>
                    <th className="px-4 py-2">较上期</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.data.holdings.map((h, i) => (
                    <tr key={`${h.name}-${i}`} className="border-t border-border/30">
                      <td className="px-4 py-2 font-medium">{h.name}</td>
                      <td className="px-4 py-2 font-mono text-xs text-muted">
                        {h.symbol ?? "—"}
                      </td>
                      <td className="px-4 py-2 tabular-nums">
                        {h.weight_pct != null ? `${h.weight_pct.toFixed(2)}%` : "—"}
                      </td>
                      <td
                        className={cn(
                          "px-4 py-2 tabular-nums",
                          returnColor(h.change_pct)
                        )}
                      >
                        {h.change_pct != null
                          ? `${h.change_pct > 0 ? "+" : ""}${h.change_pct.toFixed(2)}%`
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>
      )}

      {tab === "managers" && (
        <SectionCard className="space-y-6">
          <SectionCardHeader title="基金经理" subtitle="现任任职信息 + 档案缓存" />
          {managers.isLoading && (
            <p className="text-center text-sm text-muted">加载中…</p>
          )}
          {managers.data?.managers_on_fund?.map((m) => (
            <div
              key={m.mgr_id}
              className="rounded-lg border border-border/50 bg-background/30 p-4"
            >
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-lg font-semibold">{m.name ?? m.mgr_id}</h3>
                {m.is_current !== false && (
                  <Badge className="border-emerald-500/30 text-emerald-400">现任</Badge>
                )}
              </div>
              <p className="mt-2 text-sm text-muted">
                任职起始 {m.start_date ?? "—"}
                {m.tenure_days != null ? ` · ${m.tenure_days} 天` : ""}
                {m.tenure_return_pct != null && (
                  <span className={cn("ml-2", returnColor(m.tenure_return_pct))}>
                    任期回报 {formatPct(m.tenure_return_pct)}
                  </span>
                )}
              </p>
            </div>
          ))}
          {managers.data?.profiles?.map((p) => (
            <div
              key={p.mgr_id}
              className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4"
            >
              <h4 className="font-medium text-foreground">{p.name ?? p.mgr_id}</h4>
              {p.company && (
                <p className="mt-1 text-xs text-muted">{p.company}</p>
              )}
              {p.experience_years && (
                <p className="mt-1 text-xs text-muted">从业 {p.experience_years}</p>
              )}
              {p.resume && (
                <p className="mt-3 text-sm leading-relaxed text-muted line-clamp-6">
                  {p.resume}
                </p>
              )}
              {p.managed_fund_names && p.managed_fund_names.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-medium text-muted">在管基金</p>
                  <p className="mt-1 text-xs text-foreground/80">
                    {p.managed_fund_names.slice(0, 8).join("、")}
                    {p.managed_fund_names.length > 8 ? "…" : ""}
                  </p>
                </div>
              )}
            </div>
          ))}
          {!managers.isLoading &&
            !managers.data?.managers_on_fund?.length &&
            !managers.data?.profiles?.length && (
              <p className="text-center text-sm text-muted">
                暂无经理信息，请在录入时解析经理 ID 并爬取
              </p>
            )}
        </SectionCard>
      )}

      {tab === "rules" && (
        <SectionCard>
          <SectionCardHeader
            title="交易规则"
            subtitle="申购赎回、费率与比较基准（参考支付宝交易规则页）"
          />
          {rules.isLoading && (
            <p className="text-center text-sm text-muted">加载中…</p>
          )}
          {rulesData.length > 0 ? (
            <dl className="grid gap-3 sm:grid-cols-2">
              {rulesData.map(({ label, value }) => (
                <div
                  key={label}
                  className="rounded-lg border border-border/40 bg-background/20 px-4 py-3"
                >
                  <dt className="text-xs text-muted">{label}</dt>
                  <dd className="mt-1 text-sm text-foreground break-words">
                    {String(value)}
                  </dd>
                </div>
              ))}
            </dl>
          ) : (
            !rules.isLoading && (
              <p className="py-8 text-center text-sm text-muted">
                暂无规则数据，请重新爬取基金
              </p>
            )
          )}
        </SectionCard>
      )}

      <p className="text-center text-[10px] text-muted">
        数据来自东方财富等公开接口，仅供个人研究，不构成投资建议
      </p>
    </div>
  );
}
