"use client";

import { Loader2 } from "lucide-react";
import {
  controlInputClass,
  FormLabel,
  SegmentButton,
} from "@/components/ui/form-field";
import type { FundManagerOnFund } from "@/lib/admin-api";

export const FUND_MARKETS = ["QDII", "美股", "港股", "A股", "其他"] as const;
export const FUND_SECTORS = [
  "科技",
  "医疗",
  "消费",
  "金融",
  "新能源",
  "制造",
  "均衡",
  "其他",
] as const;
export const FUND_LOOKBACKS = [
  { id: "1y", label: "1年" },
  { id: "3y", label: "3年" },
  { id: "5y", label: "5年" },
  { id: "since_inception", label: "成立以来" },
] as const;

export type FundMarket = (typeof FUND_MARKETS)[number];
export type FundSector = (typeof FUND_SECTORS)[number];
export type FundLookback = (typeof FUND_LOOKBACKS)[number]["id"];

export type FundFormValues = {
  displayName: string;
  fundCode: string;
  market: FundMarket;
  sector: FundSector;
  navLookback: FundLookback;
  crawlEnabled: boolean;
  fundManager: string;
  fundCompany: string;
  fundType: string;
  managerIds: string[];
  managersOnFund: FundManagerOnFund[];
  enabled: boolean;
};

type Props = {
  values: FundFormValues;
  onChange: (patch: Partial<FundFormValues>) => void;
  mode: "create" | "edit";
  onResolve?: () => void;
  resolving?: boolean;
  resolveHint?: string | null;
};

export function FundFormFields({
  values,
  onChange,
  mode,
  onResolve,
  resolving,
  resolveHint,
}: Props) {
  const codeLocked = mode === "edit";
  const canResolve = !codeLocked && values.fundCode.trim().length >= 6;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <FormLabel>基金名称</FormLabel>
          <input
            className={controlInputClass}
            value={values.displayName}
            onChange={(e) => onChange({ displayName: e.target.value })}
            placeholder="例如：易方达中小盘"
          />
        </div>
        <div>
          <FormLabel>基金代码</FormLabel>
          <div className="flex gap-2">
            <input
              className={controlInputClass}
              value={values.fundCode}
              onChange={(e) => onChange({ fundCode: e.target.value })}
              placeholder="6位，如 110011"
              readOnly={codeLocked}
              disabled={codeLocked}
              title={codeLocked ? "代码创建后不可修改（与标的 ID 绑定）" : undefined}
            />
            {onResolve && (
              <button
                type="button"
                disabled={!canResolve || resolving}
                onClick={onResolve}
                className="shrink-0 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-xs font-medium text-emerald-400 transition hover:bg-emerald-500/20 disabled:opacity-50"
              >
                {resolving ? (
                  <span className="inline-flex items-center gap-1">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    解析中
                  </span>
                ) : (
                  "解析基金信息"
                )}
              </button>
            )}
          </div>
          {codeLocked && (
            <p className="mt-1 text-[10px] text-muted">代码不可改；若填错请删除后重新录入</p>
          )}
          {resolveHint && (
            <p className="mt-1 text-[10px] text-emerald-400/90">{resolveHint}</p>
          )}
        </div>
      </div>
      {values.managerIds.length > 0 && (
        <div className="rounded-lg border border-border/50 bg-background/40 px-3 py-2 text-xs text-muted">
          <span className="text-foreground/80">基金经理 ID：</span>
          {values.managerIds.join("、")}
          {values.managersOnFund.length > 0 && (
            <span className="mt-1 block text-[10px]">
              {values.managersOnFund
                .map((m) => {
                  const ret =
                    m.tenure_return_pct != null
                      ? `任期 ${m.tenure_return_pct > 0 ? "+" : ""}${m.tenure_return_pct}%`
                      : "";
                  return `${m.name ?? m.mgr_id}${ret ? `（${ret}）` : ""}`;
                })
                .join(" · ")}
            </span>
          )}
        </div>
      )}
      <div>
        <FormLabel>市场</FormLabel>
        <div className="mt-2 flex flex-wrap gap-2">
          {FUND_MARKETS.map((m) => (
            <SegmentButton
              key={m}
              active={values.market === m}
              onClick={() => onChange({ market: m })}
            >
              {m}
            </SegmentButton>
          ))}
        </div>
      </div>
      <div>
        <FormLabel>板块</FormLabel>
        <div className="mt-2 flex flex-wrap gap-2">
          {FUND_SECTORS.map((s) => (
            <SegmentButton
              key={s}
              active={values.sector === s}
              onClick={() => onChange({ sector: s })}
            >
              {s}
            </SegmentButton>
          ))}
        </div>
      </div>
      <div>
        <FormLabel>净值回溯</FormLabel>
        <div className="mt-2 flex flex-wrap gap-2">
          {FUND_LOOKBACKS.map((l) => (
            <SegmentButton
              key={l.id}
              active={values.navLookback === l.id}
              onClick={() => onChange({ navLookback: l.id })}
            >
              {l.label}
            </SegmentButton>
          ))}
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <FormLabel>基金经理（可选）</FormLabel>
          <input
            className={controlInputClass}
            value={values.fundManager}
            onChange={(e) => onChange({ fundManager: e.target.value })}
          />
        </div>
        <div>
          <FormLabel>基金公司（可选）</FormLabel>
          <input
            className={controlInputClass}
            value={values.fundCompany}
            onChange={(e) => onChange({ fundCompany: e.target.value })}
          />
        </div>
      </div>
      {values.fundType && (
        <p className="text-xs text-muted">
          基金类型：<span className="text-foreground/90">{values.fundType}</span>
        </p>
      )}
      <div className="flex flex-wrap gap-4 text-sm">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={values.crawlEnabled}
            onChange={(e) => onChange({ crawlEnabled: e.target.checked })}
          />
          允许爬取净值
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={values.enabled}
            onChange={(e) => onChange({ enabled: e.target.checked })}
          />
          在前台展示
        </label>
      </div>
    </div>
  );
}

export function fundToFormValues(f: {
  display_name: string;
  fund_code?: string;
  market?: string;
  sector?: string;
  nav_lookback?: string;
  crawl_enabled?: boolean;
  fund_manager?: string;
  fund_company?: string;
  fund_type?: string;
  manager_ids?: string[];
  managers_on_fund?: FundManagerOnFund[];
  enabled?: boolean;
}): FundFormValues {
  return {
    displayName: f.display_name,
    fundCode: f.fund_code ?? "",
    market: (FUND_MARKETS.includes((f.market as FundMarket) ?? "A股")
      ? f.market
      : "A股") as FundMarket,
    sector: (FUND_SECTORS.includes((f.sector as FundSector) ?? "均衡")
      ? f.sector
      : "均衡") as FundSector,
    navLookback: (FUND_LOOKBACKS.some((l) => l.id === f.nav_lookback)
      ? f.nav_lookback
      : "since_inception") as FundLookback,
    crawlEnabled: f.crawl_enabled ?? true,
    fundManager: f.fund_manager ?? "",
    fundCompany: f.fund_company ?? "",
    fundType: f.fund_type ?? "",
    managerIds: f.manager_ids ?? [],
    managersOnFund: f.managers_on_fund ?? [],
    enabled: f.enabled ?? true,
  };
}

export const emptyFundForm = (): FundFormValues => ({
  displayName: "",
  fundCode: "",
  market: "QDII",
  sector: "均衡",
  navLookback: "since_inception",
  crawlEnabled: true,
  fundManager: "",
  fundCompany: "",
  fundType: "",
  managerIds: [],
  managersOnFund: [],
  enabled: true,
});

export function fundFormToPayload(values: FundFormValues): Record<string, unknown> {
  return {
    display_name: values.displayName,
    fund_code: values.fundCode,
    market: values.market,
    sector: values.sector,
    nav_lookback: values.navLookback,
    crawl_enabled: values.crawlEnabled,
    enabled: values.enabled,
    fund_manager: values.fundManager || undefined,
    fund_company: values.fundCompany || undefined,
    fund_type: values.fundType || undefined,
    manager_ids: values.managerIds,
    managers_on_fund: values.managersOnFund,
  };
}
