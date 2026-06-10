"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { adminApi, type CrawlSourcesConfig } from "@/lib/admin-api";
import { getAdminToken } from "@/lib/admin-auth";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { cn } from "@/lib/utils";

type UrlChange = { field: string; from: string; to: string };

function cloneConfig(c: CrawlSourcesConfig): CrawlSourcesConfig {
  return JSON.parse(JSON.stringify(c)) as CrawlSourcesConfig;
}

export default function AdminCrawlSettingsPage() {
  const qc = useQueryClient();
  const [draft, setDraft] = useState<CrawlSourcesConfig | null>(null);
  const [msg, setMsg] = useState("");
  const [pendingUrlChanges, setPendingUrlChanges] = useState<UrlChange[] | null>(
    null
  );

  const authed = !!getAdminToken();
  const q = useQuery({
    queryKey: ["admin-crawl-config"],
    queryFn: adminApi.getCrawlConfig,
    enabled: authed,
  });

  useEffect(() => {
    if (q.data?.config) setDraft(cloneConfig(q.data.config));
  }, [q.data]);

  const endpointKeys = useMemo(
    () => Object.keys(draft?.endpoints ?? {}).sort(),
    [draft?.endpoints]
  );

  const saveMut = useMutation({
    mutationFn: (confirm: boolean) =>
      adminApi.saveCrawlConfig(draft!, confirm),
    onSuccess: (res) => {
      setPendingUrlChanges(null);
      setMsg(
        res.url_changes_applied?.length
          ? `已保存（含 ${res.url_changes_applied.length} 处接口地址变更）`
          : "配置已保存"
      );
      qc.invalidateQueries({ queryKey: ["admin-crawl-config"] });
      qc.invalidateQueries({ queryKey: ["admin-crawl-targets"] });
    },
    onError: (e: Error & { status?: number; detail?: unknown }) => {
      const detail = e.detail as
        | {
            code?: string;
            changes?: UrlChange[];
            message?: string;
          }
        | undefined;
      if (
        e.status === 409 &&
        detail?.code === "url_change_confirmation_required" &&
        detail.changes
      ) {
        setPendingUrlChanges(detail.changes);
        setMsg(detail.message ?? "请确认接口地址变更");
        return;
      }
      setMsg(e.message);
    },
  });

  const resetMut = useMutation({
    mutationFn: adminApi.resetCrawlConfig,
    onSuccess: (res) => {
      setDraft(cloneConfig(res.config));
      setMsg("已恢复为 config/crawl_sources.yaml 基线");
      qc.invalidateQueries({ queryKey: ["admin-crawl-config"] });
    },
    onError: (e: Error) => setMsg(e.message),
  });

  function setDefault(key: string, value: number) {
    setDraft((d) =>
      d ? { ...d, defaults: { ...d.defaults, [key]: value } } : d
    );
  }

  function setDefaultRaw(key: string, value: string | boolean) {
    setDraft((d) =>
      d ? { ...d, defaults: { ...d.defaults, [key]: value } } : d
    );
  }

  function setEndpoint(key: string, value: string) {
    setDraft((d) =>
      d ? { ...d, endpoints: { ...d.endpoints, [key]: value } } : d
    );
  }

  if (!draft) {
    return (
      <p className="text-sm text-muted">
        {q.isLoading ? "加载配置…" : "无法加载采集配置"}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {msg && (
        <div className="alert-banner alert-banner--info text-xs">{msg}</div>
      )}

      {pendingUrlChanges && (
        <div className="rounded-xl border border-amber-500/50 bg-amber-500/10 p-4">
          <p className="text-sm font-medium text-amber-200">
            检测到接口地址变更，确认后才会保存：
          </p>
          <ul className="mt-2 space-y-2 text-xs text-muted">
            {pendingUrlChanges.map((c) => (
              <li key={c.field}>
                <span className="text-foreground">{c.field}</span>
                <br />
                <span className="line-through opacity-60">{c.from}</span>
                <br />
                <span className="text-amber-100">{c.to}</span>
              </li>
            ))}
          </ul>
          <div className="mt-4 flex gap-2">
            <button
              type="button"
              className="rounded-lg bg-amber-600 px-4 py-2 text-xs font-medium text-white hover:bg-amber-500"
              disabled={saveMut.isPending}
              onClick={() => saveMut.mutate(true)}
            >
              确认并保存
            </button>
            <button
              type="button"
              className="rounded-lg border border-border px-4 py-2 text-xs hover:bg-card"
              onClick={() => setPendingUrlChanges(null)}
            >
              取消
            </button>
          </div>
        </div>
      )}

      <SectionCard>
        <SectionCardHeader
          title="采集参数"
          subtitle={
            q.data?.meta.override_exists
              ? `已启用覆盖文件：${q.data.meta.override_path}`
              : `基线：${q.data?.meta.base_path}（未覆盖）`
          }
        />
        <p className="mb-4 text-xs text-muted">
          当前回溯约 <strong className="text-foreground">{q.data?.lookback_days}</strong>{" "}
          自然日。也可直接编辑{" "}
          <code className="text-primary">config/crawl_sources.yaml</code> 或{" "}
          <code className="text-primary">data/crawl_config.override.yaml</code>。
        </p>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(
            [
              ["lookback_years", "行情回溯年数", 1],
              ["lookback_days_extra", "回溯额外自然日", 1],
              ["scoring_lookback_years", "评分历史分位年数", 1],
              ["crawl_retry", "行情重试次数", 1],
              ["crawl_retry_interval_sec", "重试间隔(秒)", 1],
              ["breadth_symbol_sleep_sec", "广度每股间隔(秒)", 0.1],
              ["price_jump_threshold", "价格跳变阈值", 0.01],
            ] as const
          ).map(([key, label, step]) => {
            const raw = draft.defaults?.[key];
            const numValue =
              typeof raw === "number" ? raw : typeof raw === "string" ? raw : "";
            return (
            <label key={key} className="block text-xs">
              <span className="text-muted">{label}</span>
              <input
                type="number"
                step={step}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                value={numValue}
                onChange={(e) =>
                  setDefault(key, parseFloat(e.target.value) || 0)
                }
              />
            </label>
            );
          })}
        </div>
      </SectionCard>

      <SectionCard>
        <SectionCardHeader
          title="每日自动采集"
          subtitle="API 容器内置定时器；也可用系统计划任务运行 daily_crawl --incremental"
        />
        <div className="mb-4 space-y-2 text-xs text-muted">
          <p>
            开启后每天在指定时间增量拉取指数/宏观/基金（仅补最新数据）。
            修改后保存并自动重载调度器。
          </p>
        </div>
        <div className="flex flex-wrap gap-4 text-sm">
          {(
            [
              ["auto_crawl_enabled", "启用每日自动采集"],
              ["auto_crawl_incremental", "增量模式（推荐）"],
              ["auto_crawl_include_funds", "包含主动基金"],
              ["auto_crawl_run_alerts", "采集后检查回调并邮件提醒"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={!!draft.defaults?.[key]}
                onChange={(e) => setDefaultRaw(key, e.target.checked)}
              />
              {label}
            </label>
          ))}
        </div>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="block text-xs">
            <span className="text-muted">执行时间 (HH:MM)</span>
            <input
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              value={String(draft.defaults?.auto_crawl_time ?? "07:30")}
              onChange={(e) => setDefaultRaw("auto_crawl_time", e.target.value)}
            />
          </label>
          <label className="block text-xs">
            <span className="text-muted">时区</span>
            <input
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              value={String(draft.defaults?.auto_crawl_timezone ?? "Asia/Shanghai")}
              onChange={(e) => setDefaultRaw("auto_crawl_timezone", e.target.value)}
            />
          </label>
        </div>
      </SectionCard>

      <SectionCard>
        <SectionCardHeader
          title="接口地址"
          subtitle="修改任意 URL 保存时需二次确认"
        />
        <div className="space-y-3">
          {endpointKeys.map((key) => (
            <label key={key} className="block text-xs">
              <span className="font-mono text-muted">endpoints.{key}</span>
              <input
                type="url"
                className={cn(
                  "mt-1 w-full rounded-lg border bg-background px-3 py-2 font-mono text-xs",
                  "border-amber-500/30 focus:border-amber-500/60"
                )}
                value={draft.endpoints?.[key] ?? ""}
                onChange={(e) => setEndpoint(key, e.target.value)}
              />
            </label>
          ))}
        </div>
      </SectionCard>

      <SectionCard>
        <SectionCardHeader title="Cboe Put/Call" subtitle="providers 节点" />
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block text-xs sm:col-span-2">
            <span className="text-muted">cboe_put_call_ratio_name</span>
            <input
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              value={String(draft.providers?.cboe_put_call_ratio_name ?? "")}
              onChange={(e) =>
                setDraft((d) =>
                  d
                    ? {
                        ...d,
                        providers: {
                          ...d.providers,
                          cboe_put_call_ratio_name: e.target.value,
                        },
                      }
                    : d
                )
              }
            />
          </label>
        </div>
      </SectionCard>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          disabled={saveMut.isPending || !!pendingUrlChanges}
          onClick={() => saveMut.mutate(false)}
        >
          保存配置
        </button>
        <button
          type="button"
          className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-card disabled:opacity-50"
          disabled={resetMut.isPending}
          onClick={() => {
            if (window.confirm("确定删除覆盖文件并恢复基线配置？")) {
              resetMut.mutate();
            }
          }}
        >
          恢复基线
        </button>
      </div>
    </div>
  );
}
