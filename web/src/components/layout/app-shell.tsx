"use client";

import { usePathname } from "next/navigation";
import { Suspense } from "react";
import { cn } from "@/lib/utils";
import { Sidebar } from "./sidebar";
import { MobileNav } from "./mobile-nav";

function ShellContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? "";
  const isInstrumentDetail = pathname.startsWith("/instruments/");

  return (
    <div className="min-h-screen bg-background/95">
      <Sidebar />
      <div className="flex min-h-screen flex-col md:pl-56">
        <MobileNav />
        <main
          className={cn(
            "relative flex-1 w-full p-3 md:p-5",
            isInstrumentDetail && "bg-transparent"
          )}
        >
          {children}
        </main>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center text-sm text-muted">
          加载中…
        </div>
      }
    >
      <ShellContent>{children}</ShellContent>
    </Suspense>
  );
}
