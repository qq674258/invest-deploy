"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearAdminToken, getAdminToken } from "@/lib/admin-auth";
import { cn } from "@/lib/utils";

const links = [
  { href: "/admin/funds", label: "基金管理" },
  { href: "/admin/site", label: "站点与用户" },
  { href: "/admin", label: "采集控制" },
  { href: "/admin/settings", label: "采集配置" },
  { href: "/admin/alerts", label: "告警与定时" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? "";
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const isLogin = pathname === "/admin/login";

  useEffect(() => {
    if (isLogin) {
      setReady(true);
      return;
    }
    if (!getAdminToken()) {
      router.replace("/admin/login");
      return;
    }
    setReady(true);
  }, [isLogin, router]);

  if (!ready) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-sm text-muted">
        验证登录…
      </div>
    );
  }

  if (isLogin) {
    return <div className="w-full">{children}</div>;
  }

  return (
    <div className="w-full space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border/50 pb-4">
        <div>
          <h1 className="text-xl font-semibold">管理后台</h1>
          <p className="text-xs text-muted">数据采集 · 基金维护 · 历史数据</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link href="/" className="text-xs text-primary hover:underline">
            返回前台
          </Link>
          <button
            type="button"
            className="rounded-lg border border-border px-3 py-1.5 text-xs text-muted hover:text-foreground"
            onClick={() => {
              clearAdminToken();
              router.push("/admin/login");
            }}
          >
            退出登录
          </button>
        </div>
      </header>
      <nav className="flex flex-wrap gap-2">
        {links.map((l) => {
          const active =
            l.href === "/admin"
              ? pathname === "/admin"
              : pathname === l.href || pathname.startsWith(`${l.href}/`);
          return (
          <Link
            key={l.href}
            href={l.href}
            className={cn(
              "rounded-lg border px-4 py-2 text-sm transition",
              active
                ? "border-primary/50 bg-primary/10 text-primary"
                : "border-border text-muted hover:border-border/80"
            )}
          >
            {l.label}
          </Link>
          );
        })}
      </nav>
      {children}
    </div>
  );
}
