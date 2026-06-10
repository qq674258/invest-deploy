"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { HEALTH_STALE_MS } from "@/lib/cache-config";
import { klineSchemeLabel, useDisplaySettings } from "@/lib/display-settings";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/ui/page-header";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import { SegmentButton } from "@/components/ui/form-field";

export default function SettingsPage() {
  const { klineScheme, setKlineScheme } = useDisplaySettings();

  const health = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    staleTime: HEALTH_STALE_MS,
  });

  return (
    <div className="w-full space-y-6">
      <PageHeader
        accent="slate"
        title="设置"
        description="显示偏好与连接状态"
      />

      <SectionCard variant="primary">
        <SectionCardHeader title="显示" subtitle="走势图涨跌颜色方案" />
        <div className="flex flex-wrap gap-2">
          {(["cn", "us"] as const).map((scheme) => (
            <SegmentButton
              key={scheme}
              active={klineScheme === scheme}
              onClick={() => setKlineScheme(scheme)}
              className="px-5"
            >
              {klineSchemeLabel(scheme)}
            </SegmentButton>
          ))}
        </div>
        <p className="mt-3 text-[10px] text-muted">
          当前：{klineSchemeLabel(klineScheme)}。设置保存在浏览器本地。
        </p>
      </SectionCard>

      <SectionCard variant="slate">
        <SectionCardHeader title="API 连接" />
        <div className="flex items-center gap-3">
          <span
            className={cn(
              "inline-flex h-2.5 w-2.5 rounded-full shadow-sm",
              health.isSuccess
                ? "bg-success shadow-success/50"
                : "bg-danger shadow-danger/50 animate-pulse"
            )}
          />
          <p className="text-sm">
            状态：{" "}
            <span className={health.isSuccess ? "font-medium text-success" : "font-medium text-danger"}>
              {health.isSuccess ? "正常" : "不可用"}
            </span>
          </p>
        </div>
      </SectionCard>

      <SectionCard variant="muted" className="text-xs leading-relaxed text-muted">
        <p className="font-semibold text-foreground">免责声明</p>
        <p className="mt-2">
          本系统输出仅供研究与个人参考，不构成任何投资建议。历史表现不代表未来收益。
        </p>
      </SectionCard>
    </div>
  );
}
