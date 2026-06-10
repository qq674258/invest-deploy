"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { CrawlProgressPanel } from "@/components/admin/crawl-progress-panel";
import {
  emptyFundForm,
  FundFormFields,
  fundFormToPayload,
  fundToFormValues,
  FUND_MARKETS,
  FUND_SECTORS,
  type FundFormValues,
} from "@/components/admin/fund-form-fields";
import { adminApi, type AdminInstrument } from "@/lib/admin-api";
import { useCrawlJob, RECENT_CRAWL_BARS } from "@/lib/use-crawl-job";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import {
  BtnPrimary,
  controlInputClass,
  controlSelectClass,
  FormLabel,
} from "@/components/ui/form-field";
import { cn } from "@/lib/utils";

export default function AdminFundsPage() {
  const qc = useQueryClient();
  const { job, runCrawl, clearJob, isRunning } = useCrawlJob();

  const [searchName, setSearchName] = useState("");
  const [searchCode, setSearchCode] = useState("");
  const [searchMarket, setSearchMarket] = useState("");
  const [searchSector, setSearchSector] = useState("");
  const [appliedSearch, setAppliedSearch] = useState({
    q: "",
    code: "",
    market: "",
    sector: "",
  });

  const funds = useQuery({
    queryKey: ["admin-funds", appliedSearch],
    queryFn: () =>
      adminApi.funds({
        q: appliedSearch.q || undefined,
        code: appliedSearch.code || undefined,
        market: appliedSearch.market || undefined,
        sector: appliedSearch.sector || undefined,
      }),
  });

  const [createForm, setCreateForm] = useState<FundFormValues>(emptyFundForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<FundFormValues>(emptyFundForm);
  const [msg, setMsg] = useState("");
  const [resolvingCreate, setResolvingCreate] = useState(false);
  const [resolveHint, setResolveHint] = useState<string | null>(null);

  const list = funds.data?.items ?? [];
  const total = funds.data?.total ?? 0;

  const createMut = useMutation({
    mutationFn: () => adminApi.createFund(fundFormToPayload(createForm)),
    onSuccess: async (res) => {
      const savedName = createForm.displayName;
      const savedLookback = createForm.navLookback;
      const shouldCrawl = createForm.crawlEnabled;
      setMsg(`已创建 ${res.instrument_id}`);
      setCreateForm(emptyFundForm());
      setResolveHint(null);
      qc.invalidateQueries({ queryKey: ["admin-funds"] });
      if (shouldCrawl) {
        try {
          const result = await runCrawl(res.instrument_id, {
            displayName: savedName || res.instrument_id,
            nav_lookback: savedLookback,
          });
          setMsg(
            `已创建并完成采集 ${res.instrument_id}：${result.rows} 条（${result.status}）`
          );
          qc.invalidateQueries({ queryKey: ["admin-funds"] });
        } catch {
          setMsg(`已创建 ${res.instrument_id}，但自动采集失败（见下方日志）`);
        }
      }
    },
    onError: (e) => {
      const t = e instanceof Error ? e.message : "创建失败";
      setMsg(t.includes("登录") ? t : `保存失败：${t}`);
    },
  });

  const updateMut = useMutation({
    mutationFn: () => adminApi.updateFund(editingId!, fundFormToPayload(editForm)),
    onSuccess: () => {
      setMsg(`已更新 ${editingId}`);
      setEditingId(null);
      qc.invalidateQueries({ queryKey: ["admin-funds"] });
    },
    onError: (e) => {
      setMsg(e instanceof Error ? e.message : "更新失败");
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => adminApi.deleteFund(id),
    onSuccess: (_, id) => {
      setMsg(`已删除 ${id}`);
      if (editingId === id) setEditingId(null);
      qc.invalidateQueries({ queryKey: ["admin-funds"] });
    },
  });

  function applySearch() {
    setAppliedSearch({
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
    setAppliedSearch({ q: "", code: "", market: "", sector: "" });
  }

  function startEdit(f: AdminInstrument) {
    setEditingId(f.instrument_id);
    setEditForm(fundToFormValues(f));
    setMsg("");
    setResolveHint(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleResolveCreate() {
    const code = createForm.fundCode.trim();
    if (code.length < 6) {
      setMsg("请先输入至少 6 位基金代码");
      return;
    }
    setResolvingCreate(true);
    setResolveHint(null);
    setMsg("");
    try {
      const r = await adminApi.resolveFund(code);
      setCreateForm((v) => ({
        ...v,
        displayName: r.display_name || v.displayName,
        fundManager: r.fund_manager || v.fundManager,
        fundCompany: r.fund_company || v.fundCompany,
        fundType: r.fund_type || "",
        managerIds: r.manager_ids,
        managersOnFund: r.managers,
      }));
      const idPart =
        r.manager_ids.length > 0
          ? `已解析 ${r.manager_ids.length} 位现任经理`
          : "未解析到经理 ID（可保存后靠爬取重试）";
      setResolveHint(
        [r.display_name, r.fund_type, idPart].filter(Boolean).join(" · ")
      );
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "解析失败");
    } finally {
      setResolvingCreate(false);
    }
  }

  async function handleCrawl(f: AdminInstrument, recentBars?: number) {
    setMsg("");
    try {
      const result = await runCrawl(f.instrument_id, {
        displayName: f.display_name,
        nav_lookback: f.nav_lookback,
        recent_bars: recentBars,
      });
      const mode = recentBars ? `近期 ${recentBars} 条` : "全量";
      setMsg(`${f.instrument_id} ${mode} 采集完成：${result.rows} 条（${result.status}）`);
      qc.invalidateQueries({ queryKey: ["admin-funds"] });
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "采集失败");
    }
  }

  const hasActiveSearch = useMemo(
    () => !!(appliedSearch.q || appliedSearch.code || appliedSearch.market || appliedSearch.sector),
    [appliedSearch]
  );

  return (
    <div className="space-y-6">
      {msg && !isRunning && (
        <div className="alert-banner alert-banner--info text-xs">{msg}</div>
      )}

      <CrawlProgressPanel job={job} onClose={clearJob} />

      {editingId && (
        <SectionCard variant="primary" className="space-y-4">
          <SectionCardHeader
            title={`编辑基金 · ${editingId}`}
            subtitle="修改后保存；基金代码不可变更"
          />
          <FundFormFields
            mode="edit"
            values={editForm}
            onChange={(patch) => setEditForm((v) => ({ ...v, ...patch }))}
          />
          <div className="flex flex-wrap gap-2">
            <BtnPrimary
              disabled={updateMut.isPending || !editForm.displayName}
              onClick={() => updateMut.mutate()}
            >
              {updateMut.isPending ? "保存中…" : "保存修改"}
            </BtnPrimary>
            <button
              type="button"
              className="rounded-lg border border-border px-4 py-2 text-sm text-muted hover:text-foreground"
              onClick={() => setEditingId(null)}
            >
              取消编辑
            </button>
          </div>
        </SectionCard>
      )}

      <SectionCard variant="emerald" className="space-y-4">
        <SectionCardHeader
          title="录入新基金"
          subtitle="含 QDII；保存后可立即爬取净值"
        />
        <FundFormFields
          mode="create"
          values={createForm}
          onChange={(patch) => setCreateForm((v) => ({ ...v, ...patch }))}
          onResolve={handleResolveCreate}
          resolving={resolvingCreate}
          resolveHint={resolveHint}
        />
        <BtnPrimary
          disabled={
            createMut.isPending ||
            isRunning ||
            !!editingId ||
            !createForm.displayName ||
            createForm.fundCode.length < 6
          }
          onClick={() => createMut.mutate()}
        >
          {createMut.isPending ? "保存中…" : isRunning ? "采集中…" : "保存新基金"}
        </BtnPrimary>
      </SectionCard>

      <SectionCard variant="muted" padding={false}>
        <SectionCardHeader
          title="已录入基金"
          subtitle={`共 ${total} 只${hasActiveSearch ? "（已筛选）" : ""} · 支持名称模糊 / 代码精确搜索`}
        />

        <div className="space-y-3 border-b border-border/40 px-4 py-4">
          <div className="grid gap-3 md:grid-cols-5">
            <div className="md:col-span-2">
              <FormLabel>名称（模糊）</FormLabel>
              <input
                className={controlInputClass}
                value={searchName}
                onChange={(e) => setSearchName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && applySearch()}
                placeholder="基金名称、经理等关键字"
              />
            </div>
            <div>
              <FormLabel>代码（精确）</FormLabel>
              <input
                className={controlInputClass}
                value={searchCode}
                onChange={(e) => setSearchCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                onKeyDown={(e) => e.key === "Enter" && applySearch()}
                placeholder="6 位，如 021528"
                maxLength={6}
              />
            </div>
            <div>
              <FormLabel>市场</FormLabel>
              <select
                className={controlSelectClass}
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
                className={controlSelectClass}
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
        </div>

        {funds.isLoading && (
          <p className="px-4 py-8 text-center text-sm text-muted">加载中…</p>
        )}

        {!funds.isLoading && list.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-muted">
            {hasActiveSearch ? "无匹配基金，请调整搜索条件" : "暂无录入基金"}
          </p>
        )}

        {!funds.isLoading && list.length > 0 && (
          <div className="overflow-x-auto">
            <table className="data-table w-full min-w-[880px] text-sm">
              <thead>
                <tr className="text-left text-xs text-muted">
                  <th className="px-4 py-2">名称</th>
                  <th className="px-4 py-2">代码</th>
                  <th className="px-4 py-2">市场</th>
                  <th className="px-4 py-2">板块</th>
                  <th className="px-4 py-2">回溯</th>
                  <th className="px-4 py-2">净值数据</th>
                  <th className="px-4 py-2">操作</th>
                </tr>
              </thead>
              <tbody>
                {list.map((f) => {
                  const crawling = isRunning && job?.instrumentId === f.instrument_id;
                  const isEditing = editingId === f.instrument_id;
                  return (
                    <tr
                      key={f.instrument_id}
                      className={cn(
                        "border-t border-border/30",
                        crawling && "bg-primary/5",
                        isEditing && "bg-primary/10"
                      )}
                    >
                      <td className="px-4 py-2">
                        <p className="font-medium text-foreground">{f.display_name}</p>
                        <p className="text-[10px] text-muted">{f.instrument_id}</p>
                        {f.fund_manager && (
                          <p className="text-[10px] text-muted">{f.fund_manager}</p>
                        )}
                        {(f.manager_ids?.length ?? 0) > 0 && (
                          <p className="text-[10px] text-emerald-500/80">
                            经理 ID ×{f.manager_ids!.length}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-2 font-mono text-xs">{f.fund_code}</td>
                      <td className="px-4 py-2 text-xs">{f.market ?? "—"}</td>
                      <td className="px-4 py-2 text-xs">{f.sector ?? "—"}</td>
                      <td className="px-4 py-2 text-xs">{f.nav_lookback ?? "—"}</td>
                      <td className="px-4 py-2 text-xs tabular-nums text-muted">
                        {f.data?.rows ?? 0} 条
                        <br />
                        {f.data?.last_date ?? "未采集"}
                      </td>
                      <td className="px-4 py-2">
                        <div className="flex flex-wrap gap-1.5">
                          <button
                            type="button"
                            className="rounded border border-primary/40 px-2 py-0.5 text-[11px] text-primary hover:bg-primary/10"
                            onClick={() => startEdit(f)}
                          >
                            编辑
                          </button>
                          <button
                            type="button"
                            className={cn(
                              "rounded border px-2 py-0.5 text-[11px]",
                              crawling
                                ? "border-primary/50 text-primary"
                                : "border-emerald-500/40 text-emerald-400"
                            )}
                            disabled={(isRunning && !crawling) || !f.crawl_enabled}
                            onClick={() => handleCrawl(f)}
                          >
                            {crawling ? "采集中" : "爬取"}
                          </button>
                          <button
                            type="button"
                            className="rounded border border-border px-2 py-0.5 text-[11px] text-muted hover:text-foreground"
                            disabled={(isRunning && !crawling) || !f.crawl_enabled}
                            onClick={() => handleCrawl(f, RECENT_CRAWL_BARS)}
                          >
                            采集近期
                          </button>
                          <Link
                            href={`/admin/data/${f.instrument_id}`}
                            className="rounded border border-border px-2 py-0.5 text-[11px] text-muted hover:text-foreground"
                          >
                            数据
                          </Link>
                          {f.admin_managed && (
                            <button
                              type="button"
                              className="rounded border border-danger/40 px-2 py-0.5 text-[11px] text-danger"
                              disabled={isRunning}
                              onClick={() => {
                                if (confirm(`删除 ${f.display_name}？`)) {
                                  deleteMut.mutate(f.instrument_id);
                                }
                              }}
                            >
                              删除
                            </button>
                          )}
                        </div>
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
