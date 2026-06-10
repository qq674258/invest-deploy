import { cn } from "@/lib/utils";

const tones = {
  default:
    "border-border-bright bg-card-elevated/80 shadow-card ring-1 ring-white/[0.04]",
  primary:
    "border-primary/45 bg-primary/10 shadow-card-primary ring-1 ring-primary/25",
  success:
    "border-success/50 bg-success/10 shadow-glow-success ring-1 ring-success/30",
  danger:
    "border-danger/50 bg-danger/10 shadow-glow-danger ring-1 ring-danger/30",
  warning:
    "border-warning/50 bg-warning/10 shadow-card-amber ring-1 ring-warning/30",
} as const;

export function StatBox({
  label,
  value,
  hint,
  tone = "default",
  className,
  valueClassName,
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  tone?: keyof typeof tones;
  className?: string;
  valueClassName?: string;
}) {
  return (
    <div className={cn("stat-box rounded-xl border p-4", tones[tone], className)}>
      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted">{label}</p>
      <p className={cn("mt-2 text-data-lg", valueClassName)}>{value}</p>
      {hint && <p className="mt-2 text-xs leading-relaxed text-muted">{hint}</p>}
    </div>
  );
}

export function KpiHero({
  label,
  value,
  sub,
  variant = "primary",
}: {
  label: string;
  value: React.ReactNode;
  sub?: string;
  variant?: "primary" | "emerald" | "violet" | "amber";
}) {
  const ring: Record<string, string> = {
    primary: "from-primary/60 via-primary/25 to-transparent",
    emerald: "from-emerald-400/55 via-emerald-500/25 to-transparent",
    violet: "from-violet-400/55 via-violet-500/25 to-transparent",
    amber: "from-amber-400/55 via-amber-500/25 to-transparent",
  };
  const border: Record<string, string> = {
    primary: "border-primary/50 ring-primary/30",
    emerald: "border-emerald-400/50 ring-emerald-400/25",
    violet: "border-violet-400/50 ring-violet-400/25",
    amber: "border-amber-400/50 ring-amber-400/30",
  };
  return (
    <div
      className={cn(
        "kpi-hero relative overflow-hidden rounded-2xl border bg-gradient-to-br from-card-elevated via-card to-background p-6 shadow-card ring-2",
        border[variant]
      )}
    >
      <div
        className={cn(
          "pointer-events-none absolute -right-10 -top-10 h-36 w-36 rounded-full bg-gradient-to-br opacity-50 blur-2xl",
          ring[variant]
        )}
      />
      <p className="relative text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className="relative mt-3 text-4xl font-bold tabular-nums tracking-tight text-foreground drop-shadow-sm">
        {value}
      </p>
      {sub && <p className="relative mt-2 text-sm text-muted">{sub}</p>}
    </div>
  );
}
