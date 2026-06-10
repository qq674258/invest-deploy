"use client";

import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { CrawlProgressPanel } from "@/components/admin/crawl-progress-panel";
import { adminApi } from "@/lib/admin-api";
import { getAdminToken } from "@/lib/admin-auth";
import { RECENT_CRAWL_BARS, useCrawlJob } from "@/lib/use-crawl-job";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { cn } from "@/lib/utils";

export default function AdminDashboardPage() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");

  const [authed, setAuthed] = useState(false);
  useEffect(() => {
    setAuthed(!!getAdminToken());
  }, []);

  const targets = useQuery({
    queryKey: ["admin-crawl-targets"],
    queryFn: adminApi.crawlTargets,
    enabled: authed,
  });

  const audits = useQuery({
    queryKey: ["admin-audits"],
    queryFn: adminApi.audits,
    enabled: authed,
  });

  const instruments = useQuery({
    queryKey: ["admin-instruments"],
    queryFn: adminApi.instruments,
    enabled: authed,
  });

  const { job, runCrawl, clearJob, isRunning } = useCrawlJob();

  async function handleCrawl(
    instrumentId: string,
    displayName: string,
    navLookback?: string,
    recentBars?: number
  ) {
    setMsg("");
    try {
      const result = await runCrawl(instrumentId, {
        displayName,
        nav_lookback: navLookback,
        recent_bars: recentBars,
      });
      const mode = recentBars ? `近期 ${recentBars} 条` : "全量";
      setMsg(`${instrumentId}: ${mode} 写入 ${result.rows} 条，状态 ${result.status}`);
      qc.invalidateQueries({ queryKey: ["admin-audits"] });
      qc.invalidateQueries({ queryKey: ["admin-instruments"] });
      qc.invalidateQueries({ queryKey: ["admin-crawl-targets"] });
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "采集失败");
    }
  }

  const jobMut = useMutation({
    mutationFn: (job: string) => adminApi.crawlJob(job),
    onSuccess: () => {
      setMsg("批量任务已提交");
      qc.invalidateQueries({ queryKey: ["admin-audits"] });
    },
  });

  return (
    <div className="space-y-6">
      {msg && !isRunning && (
        <div className="alert-banner alert-banner--info text-xs">{msg}</div>
      )}

      <CrawlProgressPanel job={job} onClose={clearJob} />

      <SectionCard variant="primary">
        <SectionCardHeader
          title="指数行情 · 手动拉取"
          subtitle={`默认回溯约 ${targets.data?.default_lookback_days ?? "—"} 自然日`}
        />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {targets.data?.indices.map((idx) => {
            const crawling = isRunning && job?.instrumentId === idx.instrument_id;
            return (
              <div
                key={idx.instrument_id}
                className={cn(
                  "rounded-xl border px-4 py-4 transition",
                  crawling
                    ? "border-primary/50 bg-primary/15"
                    : "border-primary/30 bg-primary/5"
                )}
              >
                <p className="font-semibold text-foreground">{idx.display_name}</p>
                <p className="mt-1 text-xs text-muted">{idx.instrument_id}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={isRunning && !crawling}
                    onClick={() => handleCrawl(idx.instrument_id, idx.display_name)}
                    className="rounded-lg border border-primary/40 px-2.5 py-1 text-[10px] text-primary hover:bg-primary/10 disabled:opacity-50"
                  >
                    {crawling ? "采集中…" : "立即采集"}
                  </button>
                  <button
                    type="button"
                    disabled={isRunning && !crawling}
                    onClick={() =>
                      handleCrawl(idx.instrument_id, idx.display_name, undefined, RECENT_CRAWL_BARS)
                    }
                    className="rounded-lg border border-border px-2.5 py-1 text-[10px] text-muted hover:bg-card disabled:opacity-50"
                  >
                    采集近期
                  </button>
                </div>
              </div>
            );
          })}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-lg border border-border px-3 py-2 text-xs hover:bg-card"
            disabled={jobMut.isPending || isRunning}
            onClick={() => jobMut.mutate("crawl_ndx")}
          >
            批量：纳指 crawl_ndx
          </button>
          <button
            type="button"
            className="rounded-lg border border-border px-3 py-2 text-xs hover:bg-card"
            disabled={jobMut.isPending || isRunning}
            onClick={() => jobMut.mutate("crawl_spx")}
          >
            批量：标普 crawl_spx
          </button>
          <button
            type="button"
            className="rounded-lg border border-border px-3 py-2 text-xs hover:bg-card"
            disabled={jobMut.isPending || isRunning}
            onClick={() => jobMut.mutate("crawl_jp_de")}
          >
            批量：日德 crawl_jp_de
          </button>
        </div>
      </SectionCard>

      <SectionCard variant="emerald">
        <SectionCardHeader title="国内基金 · 快速采集" subtitle="在「基金管理」中维护标的" />
        <div className="space-y-2">
          {targets.data?.funds.length ? (
            targets.data.funds.map((f) => (
              <div
                key={f.instrument_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-emerald-500/20 bg-background/30 px-3 py-2"
              >
                <div>
                  <p className="text-sm font-medium">{f.display_name}</p>
                  <p className="text-xs text-muted">
                    {f.fund_code} · {f.nav_lookback ?? "since_inception"}
                    {!f.crawl_enabled && " · 已关闭爬取"}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={
                      (isRunning && job?.instrumentId !== f.instrument_id) ||
                      !f.crawl_enabled
                    }
                    onClick={() =>
                      handleCrawl(f.instrument_id, f.display_name, f.nav_lookback)
                    }
                    className="rounded-lg border border-emerald-500/40 px-3 py-1.5 text-xs text-emerald-400 hover:bg-emerald-500/10 disabled:opacity-40"
                  >
                    {isRunning && job?.instrumentId === f.instrument_id
                      ? "采集中…"
                      : "立即爬净值"}
                  </button>
                  <button
                    type="button"
                    disabled={
                      (isRunning && job?.instrumentId !== f.instrument_id) ||
                      !f.crawl_enabled
                    }
                    onClick={() =>
                      handleCrawl(
                        f.instrument_id,
                        f.display_name,
                        f.nav_lookback,
                        RECENT_CRAWL_BARS
                      )
                    }
                    className="rounded-lg border border-border px-3 py-1.5 text-xs text-muted hover:bg-card disabled:opacity-40"
                  >
                    采集近期
                  </button>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted">暂无基金，请前往基金管理录入</p>
          )}
        </div>
      </SectionCard>

      <SectionCard variant="muted" padding={false}>
        <SectionCardHeader title="全部标的 · 数据维护" />
        <div className="overflow-x-auto px-2 pb-4">
          <table className="data-table w-full min-w-[640px] text-sm">
            <thead>
              <tr className="text-left text-xs text-muted">
                <th className="px-4 py-2">标的</th>
                <th className="px-4 py-2">类型</th>
                <th className="px-4 py-2">数据</th>
                <th className="px-4 py-2">操作</th>
              </tr>
            </thead>
            <tbody>
              {instruments.data?.map((row) => (
                <tr key={row.instrument_id} className="border-t border-border/30">
                  <td className="px-4 py-2">
                    <p className="font-medium">{row.display_name}</p>
                    <p className="text-xs text-muted">{row.instrument_id}</p>
                  </td>
                  <td className="px-4 py-2 text-xs text-muted">{row.asset_class}</td>
                  <td className="px-4 py-2 text-xs tabular-nums text-muted">
                    {row.data?.rows ?? 0} 条 · {row.data?.last_date ?? "—"}
                  </td>
                  <td className="px-4 py-2">
                    <Link
                      href={`/admin/data/${row.instrument_id}`}
                      className="text-xs text-primary hover:underline"
                    >
                      查看/去重
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>

      <SectionCard variant="slate" padding={false}>
        <SectionCardHeader title="采集审计" subtitle="最近任务记录" />
        <ul className="max-h-64 overflow-y-auto px-4 pb-4 text-xs">
          {audits.data?.map((a) => (
            <li
              key={a.id}
              className={cn(
                "border-b border-border/30 py-2",
                a.status === "success" ? "text-muted" : "text-warning"
              )}
            >
              <span className="font-mono">{a.job_id}</span> · {a.rows_upserted} 行 ·{" "}
              {a.status}
              {a.errors?.length > 0 && (
                <span className="block text-danger">{a.errors.join("; ")}</span>
              )}
            </li>
          ))}
        </ul>
      </SectionCard>
    </div>
  );
}
