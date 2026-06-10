"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { LayoutDashboard } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { isNavLinkActive, MAIN_NAV_LINKS } from "./nav-links";

export function Sidebar() {
  const pathname = usePathname() ?? "";
  const siteQ = useQuery({
    queryKey: ["site-config"],
    queryFn: api.siteConfig,
  });
  const siteTitle = siteQ.data?.title ?? "投资回撤提醒-定投计算器工具";

  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-56 flex-col border-r border-border/50 bg-gradient-to-b from-card via-card/98 to-background/90 shadow-[4px_0_24px_rgba(0,0,0,0.25)] backdrop-blur-xl md:flex">
      <div className="flex h-16 items-center gap-2 border-b border-border/50 bg-gradient-to-r from-primary/10 to-transparent px-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/15 shadow-inner-glow ring-1 ring-primary/25">
          <LayoutDashboard className="h-5 w-5 text-primary" />
        </div>
        <div>
          <p className="text-sm font-semibold tracking-tight">{siteTitle}</p>
          <p className="text-[10px] text-muted">指数 · 定投 · 回调提醒</p>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-3">
        {MAIN_NAV_LINKS.map(({ href, label, icon: Icon }) => {
          const active = isNavLinkActive(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg border px-3 py-2.5 text-sm transition-colors",
                active
                  ? "nav-link-active font-medium"
                  : "border-transparent text-muted hover:bg-card/60 hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border/60 p-4">
        <p className="text-[10px] leading-relaxed text-muted">
          仅供参考，数据可能存在延迟
        </p>
      </div>
    </aside>
  );
}
