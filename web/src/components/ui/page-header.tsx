import { cn } from "@/lib/utils";

const accentBar: Record<string, string> = {
  default: "from-primary via-primary/60 to-transparent",
  emerald: "from-emerald-400 via-emerald-500/50 to-transparent",
  violet: "from-violet-400 via-violet-500/50 to-transparent",
  amber: "from-amber-400 via-amber-500/50 to-transparent",
  slate: "from-slate-400 via-slate-500/40 to-transparent",
};

export function PageHeader({
  title,
  description,
  accent = "default",
  action,
  badge,
}: {
  title: string;
  description?: string;
  accent?: keyof typeof accentBar;
  action?: React.ReactNode;
  badge?: React.ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-3">
          <div
            className={cn(
              "h-9 w-1 shrink-0 rounded-full bg-gradient-to-b shadow-sm",
              accentBar[accent] ?? accentBar.default
            )}
          />
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight text-foreground">
                {title}
              </h1>
              {badge}
            </div>
            {description && (
              <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-muted">
                {description}
              </p>
            )}
          </div>
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </header>
  );
}
