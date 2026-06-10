"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { defaultQueryRetry, formatQueryError } from "@/lib/query-utils";
import { SignalTierTable } from "@/components/all-in/signal-tier-table";
import { formatMoney } from "@/lib/utils";
import { PageHeader } from "@/components/ui/page-header";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { KpiHero, StatBox } from "@/components/ui/stat-box";
import {
  FormLabel,
  controlInputClass,
  controlSelectClass,
  paramFieldClass,
  paramGridClass,
} from "@/components/ui/form-field";

function defaultBuyDate(meta: { data_start: string; data_end: string } | undefined) {
  if (!meta) return "";
  return meta.data_end;
}

function drawdownTone(
  label?: string | null
): "success" | "warning" | "danger" | "default" | "primary" {
  if (!label) return "default";
  if (label.includes("深度") || label.includes("极端")) return "success";
  if (label.includes("中度")) return "primary";
  if (label.includes("轻微")) return "danger";
  return "warning";
}

export default function AllInCalculatorPage() {
  const instruments = useQuery({
    queryKey: ["instruments"],
    queryFn: api.instruments,
  });

  const [instrumentId, setInstrumentId] = useState("NDX");
  const [amount, setAmount] = useState(30000);
  const [buyDate, setBuyDate] = useState("");
  const [buyDateTouched, setBuyDateTouched] = useState(false);

  const meta = useQuery({
    queryKey: ["lump-sum-meta", instrumentId],
    queryFn: () => api.lumpSumMeta(instrumentId),
    enabled: !!instrumentId,
    retry: defaultQueryRetry,
  });

  useEffect(() => {
    if (!buyDateTouched && meta.data) {
      setBuyDate(defaultBuyDate(meta.data));
    }
  }, [meta.data, instrumentId, buyDateTouched]);

  useEffect(() => {
    setBuyDateTouched(false);
    setBuyDate("");
  }, [instrumentId]);

  const safeAmount = Number.isFinite(amount) && amount > 0 ? amount : 0;
  const canCalc = !!instrumentId && !!buyDate && safeAmount > 0;

  const result = useQuery({
    queryKey: ["lump-sum-calc", instrumentId, buyDate, safeAmount],
    queryFn: () => api.lumpSumCalc(instrumentId, buyDate, safeAmount),
    enabled: canCalc && meta.isSuccess,
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: defaultQueryRetry,
  });

  const instrumentName = useMemo(
    () => instruments.data?.find((i) => i.instrument_id === instrumentId)?.display_name,
    [instruments.data, instrumentId]
  );

  const r = result.data;
  const positive = (r?.profit ?? 0) >= 0;
  const dd = r?.context?.signals?.drawdown;

  return (
    <div className="w-full space-y-6">
      <PageHeader
        accent="emerald"
        title="All in 收益计算"
        description="按历史收盘价一次性买入；展示买入日相对近半年高点的回撤深度，并测算持有至今收益"
      />

      <SectionCard variant="emerald" className="space-y-4">
        <SectionCardHeader title="买入参数" subtitle="修改后自动重算" />
        <div className={paramGridClass}>
          <div className={paramFieldClass}>
            <FormLabel>标的</FormLabel>
            <select
              className={controlSelectClass}
              value={instrumentId}
              onChange={(e) => setInstrumentId(e.target.value)}
            >
              {instruments.data?.map((i) => (
                <option key={i.instrument_id} value={i.instrument_id}>
                  {i.display_name}
                </option>
              ))}
            </select>
          </div>
          <div className={paramFieldClass}>
            <FormLabel>买入日</FormLabel>
            <input
              type="date"
              className={controlInputClass}
              value={buyDate}
              min={meta.data?.data_start}
              max={meta.data?.data_end}
              onChange={(e) => {
                setBuyDateTouched(true);
                setBuyDate(e.target.value);
              }}
              disabled={!meta.data}
            />
            {meta.data && (
              <p className="mt-1 text-[10px] text-muted">
                默认最新交易日 · 可选 {meta.data.data_start} → {meta.data.data_end}
              </p>
            )}
          </div>
          <div className={paramFieldClass}>
            <FormLabel>买入金额</FormLabel>
            <input
              type="number"
              min={1}
              step={100}
              className={controlInputClass}
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value) || 0)}
            />
          </div>
        </div>
        {meta.data && (
          <div className="flex flex-wrap gap-2 border-t border-border/50 pt-3">
            <button
              type="button"
              className="rounded-md border border-border-bright bg-card-elevated/80 px-2.5 py-1 text-xs text-muted hover:text-foreground"
              onClick={() => {
                setBuyDateTouched(true);
                setBuyDate(meta.data!.data_start);
              }}
            >
              样本首日
            </button>
            <button
              type="button"
              className="rounded-md border border-border-bright bg-card-elevated/80 px-2.5 py-1 text-xs text-muted hover:text-foreground"
              onClick={() => {
                setBuyDateTouched(true);
                setBuyDate(meta.data!.data_end);
              }}
            >
              最新交易日
            </button>
            <span className="self-center text-[10px] text-muted">
              最新收盘 {formatMoney(meta.data.latest_price)}
            </span>
          </div>
        )}
      </SectionCard>

      {meta.isError && (
        <div className="alert-banner alert-banner--warning text-sm">
          {formatQueryError(meta.error)}。请先在管理后台爬取该基金净值。
        </div>
      )}

      {result.isLoading && canCalc && meta.isSuccess && (
        <SectionCard variant="emerald" className="flex h-40 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500/30 border-t-emerald-400" />
        </SectionCard>
      )}

      {result.isError && (
        <div className="alert-banner alert-banner--danger text-sm">
          {formatQueryError(result.error) || "计算失败，请检查买入日是否在净值范围内。"}
        </div>
      )}

      {r && (
        <>
          <KpiHero
            variant="emerald"
            label={`总收益率 · ${instrumentName ?? r.instrument_id}`}
            value={
              <span className={positive ? "text-success" : "text-danger"}>
                {r.return_pct >= 0 ? "+" : ""}
                {r.return_pct.toFixed(2)}%
              </span>
            }
            sub={`${r.buy_date} 买入 → ${r.latest_date}（持有 ${r.holding_years} 年）${
              dd?.buy_pct != null ? ` · 近半年回撤 ${dd.buy_pct.toFixed(2)}%` : ""
            }`}
          />

          {dd && (
            <SectionCard variant="slate" className="space-y-6">
              <SectionCardHeader
                title="近半年高点回撤"
                subtitle={
                  dd.note ??
                  "买入价相对近半年（约 126 个交易日）滚动最高价的回撤深度"
                }
              />
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <StatBox
                  label="买入日回撤"
                  value={
                    dd.buy_pct != null ? `${dd.buy_pct.toFixed(2)}%` : "—"
                  }
                  hint={dd.buy_label ?? undefined}
                  tone={drawdownTone(dd.buy_label)}
                />
                <StatBox
                  label="回撤档位"
                  value={dd.buy_label ?? "—"}
                  hint={dd.advice ?? undefined}
                />
                <StatBox
                  label="近半年最高价"
                  value={dd.buy_high != null ? formatMoney(dd.buy_high) : "—"}
                  hint={`买入日 ${r.buy_date}`}
                />
                <StatBox
                  label="买入收盘价"
                  value={formatMoney(r.buy_price)}
                  hint={
                    dd.buy_high != null && dd.buy_pct != null
                      ? `较高点 ${dd.buy_pct >= 0 ? "+" : ""}${dd.buy_pct.toFixed(2)}%`
                      : undefined
                  }
                />
              </div>
              {dd.tiers && dd.tiers.length > 0 && (
                <SignalTierTable
                  title="回撤档位参考"
                  subtitle={r.context?.drawdown_window_label ?? "近半年"}
                  tiers={dd.tiers}
                  activeTierId={dd.buy_tier_id}
                  currentValue={
                    dd.buy_pct != null ? `${dd.buy_pct.toFixed(2)}%` : null
                  }
                  currentLabel={dd.buy_label ?? undefined}
                />
              )}
            </SectionCard>
          )}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatBox
              label="期末总资产"
              value={formatMoney(r.final_value)}
              hint={`买入 ${formatMoney(r.amount)}`}
              tone="primary"
            />
            <StatBox
              label="总收益"
              value={
                <>
                  {r.profit >= 0 ? "+" : ""}
                  {formatMoney(r.profit)}
                </>
              }
              tone={positive ? "success" : "danger"}
              valueClassName={positive ? "text-success" : "text-danger"}
            />
            <StatBox
              label="年化收益率"
              value={`${r.annualized_return_pct >= 0 ? "+" : ""}${r.annualized_return_pct.toFixed(2)}%`}
              hint={`持有 ${r.holding_days} 天`}
              tone="default"
            />
            <StatBox
              label="买入价 → 现价"
              value={
                <>
                  {formatMoney(r.buy_price)}
                  <span className="mx-1 text-muted">→</span>
                  {formatMoney(r.latest_price)}
                </>
              }
              hint={r.date_snapped ? `已对齐交易日（请求 ${r.buy_date_requested}）` : undefined}
            />
          </div>

          <SectionCard variant="slate">
            <SectionCardHeader title="计算说明" />
            <ul className="space-y-2 text-xs leading-relaxed text-muted">
              <li>
                假设在 <strong className="text-foreground">{r.buy_date}</strong> 以收盘价{" "}
                <strong className="text-foreground">{formatMoney(r.buy_price)}</strong> 一次性买入{" "}
                <strong className="text-foreground">{formatMoney(r.amount)}</strong>，持有至{" "}
                <strong className="text-foreground">{r.latest_date}</strong> 收盘价{" "}
                <strong className="text-foreground">{formatMoney(r.latest_price)}</strong> 估值。
              </li>
              <li>
                近半年回撤 = 买入收盘价 ÷ 近半年滚动最高价 − 1；滚动窗口约 126 个交易日。
              </li>
              <li>
                总收益率 = (现价 ÷ 买入价 − 1)；年化按持有{" "}
                {r.holding_years} 年复利折算。
              </li>
              <li>未计交易成本、分红再投资与汇率；本地 crawl 数据截至 {r.data_end}。</li>
            </ul>
          </SectionCard>
        </>
      )}
    </div>
  );
}
