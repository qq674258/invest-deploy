"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import type { CrawlLogLine, CrawlResult } from "@/lib/admin-api";

export type CrawlJobState = {
  instrumentId: string;
  displayName?: string;
  status: "idle" | "running" | "success" | "partial" | "error";
  progress: number;
  logs: CrawlLogLine[];
  result?: CrawlResult;
  errorMessage?: string;
};

type Props = {
  job: CrawlJobState | null;
  onClose?: () => void;
};

function formatTs(ts: string) {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString("zh-CN", { hour12: false });
  } catch {
    return ts.slice(11, 19);
  }
}

export function CrawlProgressPanel({ job, onClose }: Props) {
  const logContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = logContainerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [job?.logs.length]);

  if (!job || job.status === "idle") return null;

  const running = job.status === "running";
  const failed = job.status === "error";
  const done = job.status === "success" || job.status === "partial";

  return (
    <SectionCard job={job} running={running} failed={failed} done={done} onClose={onClose}>
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-sm font-semibold text-foreground">
              {running ? "正在采集…" : failed ? "采集失败" : "采集完成"}
            </p>
            <p className="text-xs text-muted">
              {job.displayName ?? job.instrumentId}
              {job.result?.fund_code && ` · ${job.result.fund_code}`}
            </p>
          </div>
          {running && (
            <span className="inline-flex items-center gap-2 text-xs text-primary">
              <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
              进行中
            </span>
          )}
          {done && job.result && (
            <span
              className={cn(
                "rounded-full px-2.5 py-0.5 text-xs font-medium",
                job.status === "success"
                  ? "bg-emerald-500/15 text-emerald-400"
                  : "bg-amber-500/15 text-amber-400"
              )}
            >
              {job.result.status} · {job.result.rows} 条
            </span>
          )}
        </div>

        <div className="relative h-2 overflow-hidden rounded-full bg-border/60">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              running && "animate-pulse bg-primary",
              failed && "bg-danger",
              done && (job.status === "success" ? "bg-emerald-500" : "bg-amber-500")
            )}
            style={{
              width: running
                ? `${Math.max(job.progress, 8)}%`
                : failed
                  ? "100%"
                  : "100%",
            }}
          />
        </div>
        {running && job.progress < 100 && (
          <p className="text-[10px] text-muted">进度约 {Math.round(job.progress)}%</p>
        )}

        {failed && job.errorMessage && (
          <div className="alert-banner alert-banner--danger text-xs">{job.errorMessage}</div>
        )}

        {done && job.result?.errors && job.result.errors.length > 0 && (
          <div className="alert-banner alert-banner--warning text-xs">
            {job.result.errors.join(" · ")}
          </div>
        )}

        <div
          ref={logContainerRef}
          className="max-h-56 overflow-y-auto rounded-lg border border-border/60 bg-background/80 p-2 font-mono text-[11px] leading-relaxed"
        >
          {job.logs.length === 0 && running && (
            <p className="text-muted">等待日志…</p>
          )}
          {job.logs.map((line, i) => (
            <div
              key={`${line.ts}-${i}`}
              className={cn(
                "border-b border-border/20 py-1 last:border-0",
                line.level === "error" && "text-danger",
                line.level === "warn" && "text-amber-400",
                line.level === "info" && "text-muted"
              )}
            >
              <span className="text-foreground/40">{formatTs(line.ts)}</span>{" "}
              {line.message}
            </div>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}

function SectionCard({
  children,
  job,
  running,
  failed,
  done,
  onClose,
}: {
  children: React.ReactNode;
  job: CrawlJobState;
  running: boolean;
  failed: boolean;
  done: boolean;
  onClose?: () => void;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border p-4 shadow-card backdrop-blur-sm",
        running && "sticky top-2 z-30 border-primary/40 bg-primary/5",
        failed && "border-danger/40 bg-danger/5",
        done && !failed && "border-emerald-500/30 bg-emerald-500/5"
      )}
    >
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
          采集任务
        </h3>
        {!running && onClose && (
          <button
            type="button"
            onClick={onClose}
            className="text-xs text-muted hover:text-foreground"
          >
            关闭
          </button>
        )}
      </div>
      {children}
    </div>
  );
}
