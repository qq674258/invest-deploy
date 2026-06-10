"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState } from "react";
import { adminApi } from "@/lib/admin-api";
import { RECENT_CRAWL_BARS } from "@/lib/use-crawl-job";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { BtnPrimary } from "@/components/ui/form-field";

export default function AdminDataPage() {
  const params = useParams();
  const id = params.id as string;
  const qc = useQueryClient();
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<number[]>([]);
  const [msg, setMsg] = useState("");
  const limit = 50;

  const data = useQuery({
    queryKey: ["admin-data", id, offset],
    queryFn: () => adminApi.listData(id, { limit, offset }),
  });

  const dedupeMut = useMutation({
    mutationFn: () => adminApi.dedupe(id),
    onSuccess: (r) => {
      setMsg(`去重删除 ${r.removed} 条`);
      setSelected([]);
      qc.invalidateQueries({ queryKey: ["admin-data", id] });
    },
  });

  const deleteMut = useMutation({
    mutationFn: () => {
      if (data.data?.data_type === "nav") {
        return adminApi.deleteNav(selected);
      }
      return adminApi.deleteOhlcv(selected);
    },
    onSuccess: (r) => {
      setMsg(`已删除 ${r.deleted} 条`);
      setSelected([]);
      qc.invalidateQueries({ queryKey: ["admin-data", id] });
    },
  });

  const crawlMut = useMutation({
    mutationFn: (body?: { recent_bars?: number }) => adminApi.crawlInstrument(id, body),
    onSuccess: (r, body) => {
      const mode = body?.recent_bars ? `近期 ${body.recent_bars} 条` : "全量";
      setMsg(`${mode}重爬完成：${r.rows} 条`);
      qc.invalidateQueries({ queryKey: ["admin-data", id] });
    },
  });

  const rows = data.data?.rows ?? [];
  const total = data.data?.total ?? 0;
  const isNav = data.data?.data_type === "nav";

  function toggleRow(rowId: number) {
    setSelected((prev) =>
      prev.includes(rowId) ? prev.filter((x) => x !== rowId) : [...prev, rowId]
    );
  }

  return (
    <div className="space-y-6">
      <Link href="/admin" className="text-xs text-primary hover:underline">
        ← 返回采集控制
      </Link>
      {msg && <div className="alert-banner alert-banner--info text-xs">{msg}</div>}

      <SectionCard variant="amber">
        <SectionCardHeader
          title={`历史数据 · ${id}`}
          subtitle={`${isNav ? "基金净值" : "指数 OHLCV"} · 共 ${total} 条`}
        />
        <div className="mb-4 flex flex-wrap gap-2">
          <BtnPrimary
            className="!w-auto px-4"
            disabled={crawlMut.isPending}
            onClick={() => crawlMut.mutate(undefined)}
          >
            {crawlMut.isPending ? "爬取中…" : "重新爬取"}
          </BtnPrimary>
          <button
            type="button"
            className="rounded-lg border border-border px-4 py-2 text-sm hover:bg-card disabled:opacity-50"
            disabled={crawlMut.isPending}
            onClick={() => crawlMut.mutate({ recent_bars: RECENT_CRAWL_BARS })}
          >
            {crawlMut.isPending ? "采集中…" : "采集近期"}
          </button>
          <button
            type="button"
            className="rounded-lg border border-border px-4 py-2 text-sm"
            disabled={dedupeMut.isPending}
            onClick={() => dedupeMut.mutate()}
          >
            按日期去重
          </button>
          <button
            type="button"
            className="rounded-lg border border-danger/40 px-4 py-2 text-sm text-danger disabled:opacity-40"
            disabled={!selected.length || deleteMut.isPending}
            onClick={() => deleteMut.mutate()}
          >
            删除选中 ({selected.length})
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="data-table w-full min-w-[720px] text-xs">
            <thead>
              <tr className="text-muted">
                <th className="px-2 py-2">选</th>
                <th className="px-2 py-2">ID</th>
                <th className="px-2 py-2">日期</th>
                {isNav ? (
                  <>
                    <th className="px-2 py-2">净值</th>
                    <th className="px-2 py-2">累计</th>
                    <th className="px-2 py-2">日涨跌</th>
                  </>
                ) : (
                  <>
                    <th className="px-2 py-2">开</th>
                    <th className="px-2 py-2">高</th>
                    <th className="px-2 py-2">低</th>
                    <th className="px-2 py-2">收</th>
                  </>
                )}
                <th className="px-2 py-2">来源</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={String(r.id)} className="border-t border-border/30">
                  <td className="px-2 py-1">
                    <input
                      type="checkbox"
                      checked={selected.includes(Number(r.id))}
                      onChange={() => toggleRow(Number(r.id))}
                    />
                  </td>
                  <td className="px-2 py-1 tabular-nums">{String(r.id)}</td>
                  <td className="px-2 py-1">{String(r.date)}</td>
                  {isNav ? (
                    <>
                      <td className="px-2 py-1 tabular-nums">{String(r.nav)}</td>
                      <td className="px-2 py-1 tabular-nums">{String(r.acc_nav ?? "—")}</td>
                      <td className="px-2 py-1 tabular-nums">
                        {r.daily_return != null
                          ? `${(Number(r.daily_return) * 100).toFixed(2)}%`
                          : "—"}
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="px-2 py-1 tabular-nums">{String(r.open)}</td>
                      <td className="px-2 py-1 tabular-nums">{String(r.high)}</td>
                      <td className="px-2 py-1 tabular-nums">{String(r.low)}</td>
                      <td className="px-2 py-1 tabular-nums">{String(r.close)}</td>
                    </>
                  )}
                  <td className="px-2 py-1 text-muted">{String(r.source)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            className="rounded border border-border px-3 py-1 text-xs disabled:opacity-40"
            disabled={offset <= 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}
          >
            上一页
          </button>
          <button
            type="button"
            className="rounded border border-border px-3 py-1 text-xs disabled:opacity-40"
            disabled={offset + limit >= total}
            onClick={() => setOffset(offset + limit)}
          >
            下一页
          </button>
        </div>
      </SectionCard>
    </div>
  );
}
