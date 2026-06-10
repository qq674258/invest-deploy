"use client";

import { useCallback, useState } from "react";
import { adminApi, type CrawlJobState } from "@/lib/admin-api";

const initialJob = (id: string, displayName?: string): CrawlJobState => ({
  instrumentId: id,
  displayName,
  status: "running",
  progress: 5,
  logs: [
    {
      ts: new Date().toISOString(),
      level: "info",
      message: "连接采集服务…",
      progress: 5,
    },
  ],
});

export const RECENT_CRAWL_BARS = 20;

export function useCrawlJob() {
  const [job, setJob] = useState<CrawlJobState | null>(null);

  const runCrawl = useCallback(
    async (
      instrumentId: string,
      options?: { displayName?: string; nav_lookback?: string; recent_bars?: number }
    ) => {
      setJob(initialJob(instrumentId, options?.displayName));
      try {
        const body: { nav_lookback?: string; recent_bars?: number } = {};
        if (options?.nav_lookback) body.nav_lookback = options.nav_lookback;
        if (options?.recent_bars) body.recent_bars = options.recent_bars;
        const result = await adminApi.crawlInstrumentStream(
          instrumentId,
          {
            onLog: (line) => {
              setJob((prev) => {
                if (!prev) return prev;
                return {
                  ...prev,
                  logs: [...prev.logs, line],
                  progress: line.progress ?? prev.progress,
                };
              });
            },
          },
          Object.keys(body).length ? body : undefined
        );
        setJob((prev) => {
          if (!prev) return prev;
          const st = result.status === "success" ? "success" : "partial";
          return {
            ...prev,
            status: st,
            progress: 100,
            result,
            logs: result.logs?.length ? result.logs : prev.logs,
          };
        });
        return result;
      } catch (e) {
        const msg = e instanceof Error ? e.message : "采集失败";
        setJob((prev) =>
          prev
            ? {
                ...prev,
                status: "error",
                progress: 100,
                errorMessage: msg,
              }
            : null
        );
        throw e;
      }
    },
    []
  );

  const clearJob = useCallback(() => setJob(null), []);

  const isRunning = job?.status === "running";

  return { job, runCrawl, clearJob, isRunning };
}
