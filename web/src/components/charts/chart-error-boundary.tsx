"use client";

import React from "react";

type Props = {
  children: React.ReactNode;
  minHeight?: number;
};

type State = { error: Error | null };

/** 避免 ECharts 等图表库在 Docker/生产环境加载失败时拖垮整页 */
export class ChartErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div
          className="flex flex-col items-center justify-center gap-2 rounded-lg border border-border/60 bg-card/40 px-4 py-8 text-center text-xs text-muted"
          style={{ minHeight: this.props.minHeight ?? 200 }}
        >
          <p>图表加载失败</p>
          <p className="max-w-md text-[10px] opacity-80">
            请刷新页面；若仍失败，执行{" "}
            <code className="text-foreground/80">
              docker compose -p invest-analyzer build web
            </code>{" "}
            后重启（详见 docs/TROUBLESHOOTING.md）
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}
