import { cn } from "@/lib/utils";

const variants = {
  default:
    "border-border-bright bg-card-elevated/95 shadow-card ring-1 ring-white/[0.04]",
  primary:
    "border-primary/50 bg-gradient-to-br from-primary/15 via-card-elevated to-card shadow-card-primary ring-1 ring-primary/25",
  emerald:
    "border-emerald-400/45 bg-gradient-to-br from-emerald-500/12 via-card-elevated to-card shadow-card-emerald ring-1 ring-emerald-400/20",
  violet:
    "border-violet-400/45 bg-gradient-to-br from-violet-500/12 via-card-elevated to-card shadow-card-violet ring-1 ring-violet-400/20",
  amber:
    "border-amber-400/50 bg-gradient-to-br from-amber-500/14 via-card-elevated to-card shadow-card-amber ring-1 ring-amber-400/25",
  slate:
    "border-slate-400/30 bg-gradient-to-br from-slate-500/10 via-card-elevated to-card shadow-card ring-1 ring-white/[0.05]",
  result:
    "border-primary/55 bg-gradient-to-br from-primary/18 via-card-elevated to-card shadow-card-primary ring-2 ring-primary/30",
  muted:
    "border-border bg-card/80 shadow-card ring-1 ring-white/[0.03]",
  danger:
    "border-danger/50 bg-gradient-to-br from-danger/12 to-card-elevated shadow-glow-danger ring-1 ring-danger/25",
  warning:
    "border-warning/50 bg-gradient-to-br from-warning/12 to-card-elevated shadow-card-amber ring-1 ring-warning/25",
} as const;

export type SectionCardVariant = keyof typeof variants;

export function SectionCard({
  children,
  className,
  variant = "default",
  padding = true,
}: {
  children: React.ReactNode;
  className?: string;
  variant?: SectionCardVariant;
  padding?: boolean;
}) {
  return (
    <div
      className={cn(
        "section-card rounded-xl border backdrop-blur-sm",
        variants[variant],
        padding && "p-5 md:p-6",
        className
      )}
    >
      {children}
    </div>
  );
}

export function SectionCardHeader({
  title,
  subtitle,
  action,
  className,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "section-card-header -mx-5 -mt-5 mb-5 flex flex-wrap items-center justify-between gap-2 px-5 py-3.5 md:-mx-6 md:-mt-6 md:px-6",
        className
      )}
    >
      <div>
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
        {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
