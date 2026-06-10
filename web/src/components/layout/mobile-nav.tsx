"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { LayoutDashboard } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { isNavLinkActive, MAIN_NAV_LINKS } from "./nav-links";

export function MobileNav() {
  const pathname = usePathname() ?? "";
  const siteQ = useQuery({
    queryKey: ["site-config"],
    queryFn: api.siteConfig,
  });
  const siteTitle = siteQ.data?.title ?? "投资回撤提醒-定投计算器工具";

  return (
    <header className="border-b border-border/50 bg-gradient-to-r from-card via-card/95 to-background/90 shadow-sm backdrop-blur-md md:hidden">
      <div className="flex items-center px-4 py-3">
        <div className="flex min-w-0 items-center gap-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/15 ring-1 ring-primary/25">
            <LayoutDashboard className="h-4 w-4 text-primary" />
          </div>
          <span className="truncate text-sm font-semibold">{siteTitle}</span>
        </div>
      </div>
      <nav className="flex gap-1 overflow-x-auto px-4 pb-3">
        {MAIN_NAV_LINKS.map(({ href, label, icon: Icon }) => {
          const active = isNavLinkActive(pathname, href);
          return (
            <Link
              key={href}
              href={href}
              title={label}
              className={cn(
                "flex shrink-0 flex-col items-center gap-0.5 rounded-lg px-2 py-1.5 min-w-[3.25rem]",
                active
                  ? "bg-primary/15 text-primary ring-1 ring-primary/30"
                  : "text-muted hover:bg-card/80"
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="max-w-[4.5rem] truncate text-[9px] leading-tight">
                {label === "ALL IN 收益" ? "ALL IN" : label.length > 4 ? label.slice(0, 4) : label}
              </span>
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
