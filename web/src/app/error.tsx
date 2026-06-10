"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto flex min-h-[50vh] max-w-lg flex-col items-center justify-center gap-4 p-6 text-center">
      <h2 className="text-lg font-semibold text-foreground">页面加载出错</h2>
      <p className="text-sm text-muted">
        多为前端资源或图表模块异常。请先尝试刷新；若刚更新代码，需重建 Web 镜像。
      </p>
      <pre className="max-h-32 w-full overflow-auto rounded-lg border border-border bg-card/80 p-3 text-left text-[10px] text-muted">
        {error.message}
      </pre>
      <div className="flex flex-wrap justify-center gap-2">
        <button
          type="button"
          onClick={() => reset()}
          className="rounded-lg border border-primary/40 bg-primary/10 px-4 py-2 text-sm text-primary hover:bg-primary/15"
        >
          重试
        </button>
        <a
          href="/"
          className="rounded-lg border border-border px-4 py-2 text-sm text-muted hover:text-foreground"
        >
          返回首页
        </a>
      </div>
      <p className="text-[11px] text-muted">
        重建命令：{" "}
        <code className="text-foreground/80">
          docker compose -p invest-analyzer build web &amp;&amp; docker compose -p
          invest-analyzer up -d web
        </code>
      </p>
    </div>
  );
}
