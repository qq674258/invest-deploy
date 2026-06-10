"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import {
  calcAllHorizons,
  calcCompoundDca,
  COMPOUND_HORIZON_YEARS,
  FREQUENCY_OPTIONS,
  type CompoundFrequency,
} from "@/lib/compound";
import { formatMoney, cn } from "@/lib/utils";
import { PageHeader } from "@/components/ui/page-header";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { KpiHero, StatBox } from "@/components/ui/stat-box";
import {
  FormLabel,
  SegmentButton,
  controlInputClass,
  controlSelectClass,
} from "@/components/ui/form-field";

export default function CompoundCalculatorPage() {
  const instruments = useQuery({
    queryKey: ["instruments"],
    queryFn: api.instruments,
  });

  const [instrumentId, setInstrumentId] = useState("NDX");
  const [amount, setAmount] = useState(500);
  const [years, setYears] = useState(10);
  const [frequency, setFrequency] = useState<CompoundFrequency>("MONTHLY");
  const [returnPct, setReturnPct] = useState(10);
  const [returnTouched, setReturnTouched] = useState(false);

  const stats = useQuery({
    queryKey: ["return-stats", instrumentId],
    queryFn: () => api.returnStats(instrumentId),
    enabled: !!instrumentId,
  });

  const defaultReturn = stats.data?.annualized_return_pct ?? 10;
  const effectiveReturn = returnTouched ? returnPct : defaultReturn;
  const safeAmount = Number.isFinite(amount) && amount > 0 ? amount : 0;

  const result = useMemo(
    () =>
      calcCompoundDca({
        amount: safeAmount,
        annualReturnPct: effectiveReturn,
        years,
        frequency,
      }),
    [safeAmount, effectiveReturn, years, frequency]
  );

  const horizonResults = useMemo(
    () => calcAllHorizons(safeAmount, effectiveReturn, frequency),
    [safeAmount, effectiveReturn, frequency]
  );

  return (
    <div className="w-full space-y-6">
      <PageHeader
        accent="violet"
        title="复利计算器"
        description="下方表格固定展示 5～50 年总收益；左侧「投资时长」仅影响上方单次测算结果"
      />

      <SectionCard variant="violet" padding={false}>
        <SectionCardHeader
          title="多期限总收益（固定展示）"
          subtitle={`${COMPOUND_HORIZON_YEARS.join(" / ")} 年 · 每期 ${formatMoney(safeAmount)} · 年化 ${effectiveReturn.toFixed(1)}%`}
        />
        <div className="overflow-x-auto">
          <table className="data-table w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-border/40 text-left text-muted">
                <th className="px-5 py-3 font-medium">投资年限</th>
                <th className="px-5 py-3 font-medium">累计投入</th>
                <th className="px-5 py-3 font-medium">期末总资产</th>
                <th className="px-5 py-3 font-medium">总收益</th>
                <th className="px-5 py-3 font-medium">收益率</th>
              </tr>
            </thead>
            <tbody>
              {horizonResults.map((row) => (
                <tr
                  key={row.years}
                  className={cn(
                    "border-b border-border/30 transition-colors",
                    row.years === years &&
                      "bg-violet-500/10 ring-1 ring-inset ring-violet-500/25"
                  )}
                >
                  <td className="px-5 py-3 font-medium">
                    {row.years} 年
                    {row.years === years && (
                      <span className="ml-2 rounded bg-violet-500/20 px-1.5 py-0.5 text-[10px] text-violet-300">
                        =上方时长
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3 tabular-nums">{formatMoney(row.totalInvested)}</td>
                  <td className="px-5 py-3 tabular-nums">{formatMoney(row.finalValue)}</td>
                  <td
                    className={cn(
                      "px-5 py-3 tabular-nums font-medium",
                      row.profit >= 0 ? "text-success" : "text-danger"
                    )}
                  >
                    {formatMoney(row.profit)}
                  </td>
                  <td
                    className={cn(
                      "px-5 py-3 tabular-nums",
                      row.profit >= 0 ? "text-success" : "text-danger"
                    )}
                  >
                    {row.profitPct >= 0 ? "+" : ""}
                    {row.profitPct.toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      <div className="grid gap-6 lg:grid-cols-2">
        <SectionCard variant="violet" className="space-y-5">
          <SectionCardHeader title="测算参数" subtitle="参考标的与收益假设" />
          <div>
            <FormLabel>参考标的（用于默认年化收益）</FormLabel>
            <select
              className={controlSelectClass}
              value={instrumentId}
              onChange={(e) => {
                setInstrumentId(e.target.value);
                setReturnTouched(false);
              }}
            >
              {instruments.data?.map((i) => (
                <option key={i.instrument_id} value={i.instrument_id}>
                  {i.display_name}
                </option>
              ))}
            </select>
            {stats.data && (
              <p className="mt-2 text-xs text-muted">
                历史年化约{" "}
                <span className="font-medium text-violet-300">
                  {stats.data.annualized_return_pct}%
                </span>
                （{stats.data.sample_years} 年样本）
              </p>
            )}
          </div>

          <div>
            <FormLabel>定投频率</FormLabel>
            <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
              {FREQUENCY_OPTIONS.map((f) => (
                <SegmentButton
                  key={f.id}
                  active={frequency === f.id}
                  onClick={() => setFrequency(f.id)}
                  className="py-2"
                >
                  {f.label}
                </SegmentButton>
              ))}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <FormLabel>每期定投金额（元）</FormLabel>
              <input
                type="number"
                min={1}
                step={50}
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
                className={controlInputClass}
              />
            </div>
            <div>
              <FormLabel>单次测算时长（年）</FormLabel>
              <input
                type="number"
                min={1}
                max={50}
                step={1}
                value={years}
                onChange={(e) => setYears(Number(e.target.value))}
                className={controlInputClass}
              />
              <div className="mt-2 flex flex-wrap gap-1">
                {COMPOUND_HORIZON_YEARS.map((y) => (
                  <button
                    key={y}
                    type="button"
                    onClick={() => setYears(y)}
                    className={cn(
                      "rounded border px-2 py-0.5 text-[10px] transition",
                      years === y
                        ? "border-violet-500/60 bg-violet-500/15 text-violet-300"
                        : "border-border text-muted hover:border-violet-500/30"
                    )}
                  >
                    {y}年
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <FormLabel>预计年化收益率（%）</FormLabel>
              {!returnTouched && stats.data && (
                <button
                  type="button"
                  className="text-xs text-violet-400 hover:underline"
                  onClick={() => {
                    setReturnPct(defaultReturn);
                    setReturnTouched(false);
                  }}
                >
                  使用系统默认 {defaultReturn}%
                </button>
              )}
            </div>
            <input
              type="number"
              step={0.1}
              value={returnTouched ? returnPct : defaultReturn}
              onChange={(e) => {
                setReturnTouched(true);
                setReturnPct(Number(e.target.value));
              }}
              className={controlInputClass}
            />
          </div>
        </SectionCard>

        <div className="space-y-4">
          <KpiHero
            variant="violet"
            label={`单次测算（${years} 年）`}
            value={formatMoney(result.finalValue)}
            sub="期末总资产"
          />
          <div className="grid gap-3 sm:grid-cols-2">
            <StatBox
              label="累计投入"
              value={formatMoney(result.totalInvested)}
              hint={`${result.periods} 期`}
            />
            <StatBox
              label="总收益"
              value={formatMoney(result.profit)}
              hint={`${result.profitPct >= 0 ? "+" : ""}${result.profitPct.toFixed(1)}%`}
              tone={result.profit >= 0 ? "success" : "danger"}
              valueClassName={result.profit >= 0 ? "text-success" : "text-danger"}
            />
          </div>
          <p className="rounded-xl border border-border/40 bg-card/40 px-4 py-3 text-xs leading-relaxed text-muted">
            假设每期期末投入、收益率恒定复利。顶部表格始终包含 5/10/15/20/30/40/50 年结果。
          </p>
        </div>
      </div>
    </div>
  );
}
