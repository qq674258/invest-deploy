"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { adminApi, type AlertConfig, type CrawlSourcesConfig, type DrawdownAlertResult } from "@/lib/admin-api";
import { getAdminToken } from "@/lib/admin-auth";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import {
  BtnPrimary,
  controlInputClass,
  FormLabel,
} from "@/components/ui/form-field";

function cloneAlert(c: AlertConfig): AlertConfig {
  return JSON.parse(JSON.stringify(c)) as AlertConfig;
}

function cloneCrawl(c: CrawlSourcesConfig): CrawlSourcesConfig {
  return JSON.parse(JSON.stringify(c)) as CrawlSourcesConfig;
}

const AUTO_CRAWL_KEYS = [
  ["auto_crawl_enabled", "启用每日自动采集"],
  ["auto_crawl_incremental", "增量模式（推荐）"],
  ["auto_crawl_include_funds", "包含主动基金"],
  ["auto_crawl_run_alerts", "采集后检查回调并邮件提醒"],
] as const;

function formatThresholds(values?: number[]): string {
  return (values?.length ? values : [5, 10, 15]).join(", ");
}

function parseThresholds(text: string): number[] {
  const nums = text
    .split(/[,，\s]+/)
    .map((x) => parseInt(x.trim(), 10))
    .filter((n) => !Number.isNaN(n) && n > 0);
  const unique = Array.from(new Set(nums)).sort((a, b) => a - b);
  return unique.length ? unique : [5, 10, 15];
}

export default function AdminAlertsPage() {
  const qc = useQueryClient();
  const [draft, setDraft] = useState<AlertConfig | null>(null);
  const [crawlDraft, setCrawlDraft] = useState<CrawlSourcesConfig | null>(null);
  const [msg, setMsg] = useState("");
  const [toAddrs, setToAddrs] = useState("");
  const [thresholdsText, setThresholdsText] = useState("5, 10, 15");
  const [checkResult, setCheckResult] = useState<DrawdownAlertResult | null>(null);

  const authed = !!getAdminToken();
  const q = useQuery({
    queryKey: ["admin-alert-config"],
    queryFn: adminApi.getAlertConfig,
    enabled: authed,
  });

  const crawlQ = useQuery({
    queryKey: ["admin-crawl-config"],
    queryFn: adminApi.getCrawlConfig,
    enabled: authed,
  });

  useEffect(() => {
    if (q.data?.config) {
      setDraft(cloneAlert(q.data.config));
      setToAddrs((q.data.config.email?.to_addrs ?? []).join(", "));
      setThresholdsText(formatThresholds(q.data.config.drawdown?.thresholds_pct));
    }
  }, [q.data]);

  useEffect(() => {
    if (crawlQ.data?.config) setCrawlDraft(cloneCrawl(crawlQ.data.config));
  }, [crawlQ.data]);

  function setCrawlDefault(key: string, value: string | boolean) {
    setCrawlDraft((d) =>
      d ? { ...d, defaults: { ...d.defaults, [key]: value } } : d
    );
  }

  const saveCrawlMut = useMutation({
    mutationFn: () => adminApi.saveCrawlConfig(crawlDraft!, false),
    onSuccess: () => {
      setMsg("定时采集配置已保存，调度器已重载");
      qc.invalidateQueries({ queryKey: ["admin-crawl-config"] });
      qc.invalidateQueries({ queryKey: ["admin-alert-config"] });
    },
    onError: (e: Error) => setMsg(e.message),
  });

  const saveMut = useMutation({
    mutationFn: () => {
      if (!draft) throw new Error("无配置");
      const cfg = cloneAlert(draft);
      const thresholds_pct = parseThresholds(thresholdsText);
      cfg.drawdown = { ...cfg.drawdown, thresholds_pct };
      cfg.email = {
        ...cfg.email,
        to_addrs: toAddrs
          .split(/[,;，；\s]+/)
          .map((s) => s.trim())
          .filter(Boolean),
      };
      return adminApi.saveAlertConfig(cfg);
    },
    onSuccess: () => {
      const parsed = parseThresholds(thresholdsText);
      setThresholdsText(formatThresholds(parsed));
      setDraft((d) =>
        d ? { ...d, drawdown: { ...d.drawdown, thresholds_pct: parsed } } : d
      );
      setMsg("告警配置已保存");
      qc.invalidateQueries({ queryKey: ["admin-alert-config"] });
    },
    onError: (e: Error) => setMsg(e.message),
  });

  const testMut = useMutation({
    mutationFn: () => adminApi.testAlertEmail(),
    onSuccess: () => setMsg("测试邮件已发送"),
    onError: (e: Error) => setMsg(e.message),
  });

  const testDrawdownMut = useMutation({
    mutationFn: () => adminApi.testDrawdownAlertEmail(),
    onSuccess: () => setMsg("模拟回调告警邮件已发送，请查收"),
    onError: (e: Error) => setMsg(e.message),
  });

  const checkMut = useMutation({
    mutationFn: (dry: boolean) => adminApi.checkDrawdownAlerts(dry),
    onSuccess: (res) => {
      setCheckResult(res);
      if (res.status === "skipped") {
        setMsg(`检查跳过：${res.reason ?? res.status}`);
        return;
      }
      if (res.alerts?.length) {
        setMsg(
          `检查完成：${res.alerts.length} 条告警${res.dry_run ? "（试运行，未发邮件）" : "，已尝试发送邮件"}`
        );
        return;
      }
      const lines = (res.checked ?? [])
        .filter((c) => c.drawdown_pct != null)
        .map((c) => `${c.display_name ?? c.instrument_id} ${c.drawdown_pct!.toFixed(2)}%`);
      const summary = lines.length ? `当前回调：${lines.join("、")}` : "无有效行情数据";
      setMsg(`检查完成：均未达监测线，本次不发邮件。${summary}`);
    },
    onError: (e: Error) => setMsg(e.message),
  });

  const runNowMut = useMutation({
    mutationFn: adminApi.runSchedulerNow,
    onSuccess: () => {
      setMsg("已触发一次定时采集任务（后台执行）");
      qc.invalidateQueries({ queryKey: ["admin-alert-config"] });
    },
    onError: (e: Error) => setMsg(e.message),
  });

  if (!draft || !crawlDraft) {
    return (
      <p className="text-sm text-muted">
        {q.isLoading || crawlQ.isLoading ? "加载配置…" : "无法加载配置"}
      </p>
    );
  }

  const sched = q.data?.scheduler;
  const indices = q.data?.indices ?? [];
  const selected = new Set(draft.drawdown?.instrument_ids ?? []);

  return (
    <div className="space-y-6">
      {msg && <div className="alert-banner alert-banner--info text-xs">{msg}</div>}

      <SectionCard className="space-y-4">
        <SectionCardHeader
          title="每日自动采集"
          subtitle="勾选后保存；需保持 api 容器常驻运行"
        />
        <div className="space-y-2 rounded-lg border border-border/50 bg-background/30 px-3 py-2.5 text-sm">
          <p>
            调度器：
            <span className={sched?.running ? "text-emerald-400" : "text-amber-400"}>
              {sched?.running ? "运行中" : "未运行"}
            </span>
            {!crawlDraft.defaults?.auto_crawl_enabled && (
              <span className="text-muted">（请先勾选「启用每日自动采集」并保存）</span>
            )}
          </p>
          {sched?.jobs?.[0]?.next_run && (
            <p className="text-muted">下次执行：{sched.jobs[0].next_run}</p>
          )}
          <p className="text-muted">
            采集后告警：
            {sched?.auto_crawl_run_alerts ? "已开启" : "未开启"}
            {" · "}
            邮件：
            {sched?.email_enabled ? "已启用" : "未启用"}
            {" · "}
            回调监测：
            {sched?.drawdown_alert_enabled ? "已启用" : "未启用"}
          </p>
        </div>
        <div className="flex flex-wrap gap-4 text-sm">
          {AUTO_CRAWL_KEYS.map(([key, label]) => (
            <label key={key} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={!!crawlDraft.defaults?.[key]}
                onChange={(e) => setCrawlDefault(key, e.target.checked)}
              />
              {label}
            </label>
          ))}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <FormLabel>每天执行时间</FormLabel>
            <input
              className={controlInputClass}
              value={String(crawlDraft.defaults?.auto_crawl_time ?? "07:30")}
              onChange={(e) => setCrawlDefault("auto_crawl_time", e.target.value)}
              placeholder="07:30"
            />
          </div>
          <div>
            <FormLabel>时区</FormLabel>
            <input
              className={controlInputClass}
              value={String(crawlDraft.defaults?.auto_crawl_timezone ?? "Asia/Shanghai")}
              onChange={(e) => setCrawlDefault("auto_crawl_timezone", e.target.value)}
            />
          </div>
        </div>
        <p className="text-xs text-muted">
          增量模式只补最新数据，减轻限流压力。勾选「采集后检查回调并邮件提醒」后，定时任务会在采集完成后自动计算回调并按本页阈值发信（需同时启用邮件与本页回调告警）。更多采集参数见{" "}
          <Link href="/admin/settings" className="text-primary hover:underline">
            采集配置
          </Link>
          。
        </p>
        <div className="flex flex-wrap gap-2">
          <BtnPrimary
            className="!w-auto px-6"
            disabled={saveCrawlMut.isPending}
            onClick={() => saveCrawlMut.mutate()}
          >
            {saveCrawlMut.isPending ? "保存中…" : "保存定时采集"}
          </BtnPrimary>
          <button
            type="button"
            className="rounded-lg border border-border px-4 py-2 text-xs hover:bg-card"
            disabled={runNowMut.isPending}
            onClick={() => runNowMut.mutate()}
          >
            {runNowMut.isPending ? "执行中…" : "立即执行一次"}
          </button>
        </div>
      </SectionCard>

      <SectionCard className="space-y-4">
        <SectionCardHeader title="邮件 SMTP" subtitle="用于回撤告警通知" />
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={!!draft.email?.enabled}
            onChange={(e) =>
              setDraft((d) => ({
                ...d,
                email: { ...d?.email, enabled: e.target.checked },
              }))
            }
          />
          启用邮件发送
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <FormLabel>SMTP 服务器</FormLabel>
            <input
              className={controlInputClass}
              value={draft.email?.smtp_host ?? ""}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  email: { ...d?.email, smtp_host: e.target.value },
                }))
              }
              placeholder="smtp.example.com"
            />
          </div>
          <div>
            <FormLabel>端口</FormLabel>
            <input
              type="number"
              className={controlInputClass}
              value={draft.email?.smtp_port ?? 465}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  email: { ...d?.email, smtp_port: Number(e.target.value) },
                }))
              }
            />
          </div>
          <div>
            <FormLabel>用户名</FormLabel>
            <input
              className={controlInputClass}
              value={draft.email?.smtp_user ?? ""}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  email: { ...d?.email, smtp_user: e.target.value },
                }))
              }
            />
          </div>
          <div>
            <FormLabel>密码</FormLabel>
            <input
              type="password"
              className={controlInputClass}
              placeholder={draft.email?.smtp_password_set ? "已设置，留空不修改" : ""}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  email: { ...d?.email, smtp_password: e.target.value },
                }))
              }
            />
          </div>
          <div>
            <FormLabel>发件人</FormLabel>
            <input
              className={controlInputClass}
              placeholder="notify@qq.com 或 监测 <notify@qq.com>"
              value={draft.email?.from_addr ?? ""}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  email: { ...d?.email, from_addr: e.target.value },
                }))
              }
            />
          </div>
          <div>
            <FormLabel>收件人（逗号分隔）</FormLabel>
            <input
              className={controlInputClass}
              placeholder="you@example.com"
              value={toAddrs}
              onChange={(e) => setToAddrs(e.target.value)}
            />
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-muted">
          <input
            type="checkbox"
            checked={draft.email?.smtp_use_ssl !== false}
            onChange={(e) =>
              setDraft((d) => ({
                ...d,
                email: { ...d?.email, smtp_use_ssl: e.target.checked },
              }))
            }
          />
          使用 SSL（465）
        </label>
        <button
          type="button"
          className="rounded-lg border border-border px-4 py-2 text-xs hover:bg-card"
          disabled={testMut.isPending}
          onClick={() => testMut.mutate()}
        >
          发送测试邮件
        </button>
      </SectionCard>

      <SectionCard className="space-y-4">
        <SectionCardHeader
          title="回撤邮件告警"
          subtitle="相对滚动高点回撤达到 5% / 10% / 15% 时各通知一次；回升后可再次触发"
        />
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={!!draft.drawdown?.enabled}
            onChange={(e) =>
              setDraft((d) => ({
                ...d,
                drawdown: { ...d?.drawdown, enabled: e.target.checked },
              }))
            }
          />
          启用回撤告警
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <FormLabel>回撤计算窗口（交易日）</FormLabel>
            <input
              type="number"
              className={controlInputClass}
              value={draft.drawdown?.lookback_days ?? 252}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  drawdown: {
                    ...d?.drawdown,
                    lookback_days: Number(e.target.value) || 252,
                  },
                }))
              }
            />
          </div>
          <div>
            <FormLabel>回升重置线（%）</FormLabel>
            <input
              type="number"
              className={controlInputClass}
              value={draft.drawdown?.recover_above_pct ?? 4}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  drawdown: {
                    ...d?.drawdown,
                    recover_above_pct: Number(e.target.value) || 4,
                  },
                }))
              }
            />
          </div>
        </div>
        <div>
          <FormLabel>告警阈值（%）</FormLabel>
          <input
            className={controlInputClass}
            placeholder="5, 10, 15"
            inputMode="text"
            value={thresholdsText}
            onChange={(e) => setThresholdsText(e.target.value)}
            onBlur={() => {
              const parsed = parseThresholds(thresholdsText);
              setThresholdsText(formatThresholds(parsed));
              setDraft((d) =>
                d
                  ? {
                      ...d,
                      drawdown: { ...d.drawdown, thresholds_pct: parsed },
                    }
                  : d
              );
            }}
          />
          <p className="mt-1 text-xs text-muted">多个阈值用英文或中文逗号分隔，如 5, 10, 15</p>
        </div>
        <div>
          <FormLabel>监控指数</FormLabel>
          <div className="mt-2 flex flex-wrap gap-2">
            {indices.map((idx) => (
              <label
                key={idx.instrument_id}
                className="flex items-center gap-1.5 rounded-lg border border-border/60 px-3 py-1.5 text-xs"
              >
                <input
                  type="checkbox"
                  checked={selected.has(idx.instrument_id)}
                  onChange={(e) => {
                    const next = new Set(selected);
                    if (e.target.checked) next.add(idx.instrument_id);
                    else next.delete(idx.instrument_id);
                    setDraft((d) => ({
                      ...d,
                      drawdown: {
                        ...d?.drawdown,
                        instrument_ids: Array.from(next),
                      },
                    }));
                  }}
                />
                {idx.display_name}
              </label>
            ))}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-lg border border-border px-4 py-2 text-xs hover:bg-card"
            disabled={checkMut.isPending}
            onClick={() => checkMut.mutate(true)}
          >
            试运行检查
          </button>
          <button
            type="button"
            className="rounded-lg border border-amber-500/40 px-4 py-2 text-xs text-amber-400 hover:bg-amber-500/10"
            disabled={checkMut.isPending}
            onClick={() => checkMut.mutate(false)}
          >
            立即检查并发送
          </button>
          <button
            type="button"
            className="rounded-lg border border-primary/40 px-4 py-2 text-xs text-primary hover:bg-primary/10"
            disabled={testDrawdownMut.isPending}
            onClick={() => testDrawdownMut.mutate()}
          >
            {testDrawdownMut.isPending ? "发送中…" : "发送模拟告警邮件"}
          </button>
        </div>
        {checkResult && (checkResult.checked?.length ?? 0) > 0 && (
          <div className="overflow-x-auto rounded-lg border border-border/50">
            <table className="w-full min-w-[480px] text-left text-xs">
              <thead className="bg-background/40 text-muted">
                <tr>
                  <th className="px-3 py-2 font-medium">指数</th>
                  <th className="px-3 py-2 font-medium">近 {draft.drawdown?.lookback_days ?? 252} 日高点回调</th>
                  <th className="px-3 py-2 font-medium">已通知档位</th>
                  <th className="px-3 py-2 font-medium">说明</th>
                </tr>
              </thead>
              <tbody>
                {checkResult.checked!.map((row) => {
                  const thresholds = draft.drawdown?.thresholds_pct ?? [5, 10, 15];
                  const minThr = Math.min(...thresholds);
                  let note = "—";
                  if (row.error === "no_data") note = "无行情数据";
                  else if (row.error === "no_drawdown") note = "数据不足以计算";
                  else if (row.drawdown_pct != null) {
                    const abs = Math.abs(row.drawdown_pct);
                    if (abs < minThr) {
                      note = `未达 ${minThr}% 线（还差 ${(minThr - abs).toFixed(2)}%）`;
                    } else {
                      const pending = thresholds.filter(
                        (t) => abs >= t && !(row.notified ?? []).includes(t)
                      );
                      note =
                        pending.length > 0
                          ? `将触发 ${pending.join("/")}% 档`
                          : "已达档位且已通知过";
                    }
                  }
                  return (
                    <tr key={row.instrument_id} className="border-t border-border/40">
                      <td className="px-3 py-2">
                        {row.display_name ?? row.instrument_id}
                        <span className="ml-1 text-muted">({row.instrument_id})</span>
                      </td>
                      <td className="px-3 py-2 font-mono">
                        {row.drawdown_pct != null ? `${row.drawdown_pct.toFixed(2)}%` : "—"}
                      </td>
                      <td className="px-3 py-2">
                        {(row.notified ?? []).length > 0
                          ? (row.notified ?? []).map((t) => `${t}%`).join("、")
                          : "无"}
                      </td>
                      <td className="px-3 py-2 text-muted">{note}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <p className="text-xs text-muted">
          仅当回调达到监测线且该档位尚未通知过时才会发邮件；价格回升至 -{draft.drawdown?.recover_above_pct ?? 4}% 以上会重置档位。
        </p>
      </SectionCard>

      <div className="flex flex-wrap gap-2">
        <BtnPrimary
          className="!w-auto px-8"
          disabled={saveMut.isPending}
          onClick={() => saveMut.mutate()}
        >
          {saveMut.isPending ? "保存中…" : "保存邮件与回撤告警"}
        </BtnPrimary>
      </div>
    </div>
  );
}
