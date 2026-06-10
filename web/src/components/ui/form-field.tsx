import { cn } from "@/lib/utils";

export function FormLabel({ children }: { children: React.ReactNode }) {
  return <label className="text-xs font-medium text-muted">{children}</label>;
}

export const controlSelectClass =
  "control-input mt-2 w-full min-w-0 rounded-lg border border-border/80 bg-background/80 px-3 py-2.5 text-sm shadow-inner-glow transition focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/20";

export const controlInputClass =
  "control-input mt-2 w-full min-w-0 rounded-lg border border-border/80 bg-background/80 px-3 py-2.5 tabular-nums text-sm shadow-inner-glow transition focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/20";

/** 参数表单：大屏每行 5 列，输入框等宽铺满格内 */
export const paramGridClass =
  "grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-5";

export const paramFieldClass = "min-w-0";

export function SegmentButton({
  active,
  onClick,
  children,
  className,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-lg border py-2.5 text-sm font-medium transition-all",
        active
          ? "border-primary/60 bg-primary/15 text-primary shadow-sm shadow-primary/10"
          : "border-border/70 bg-background/40 text-muted hover:border-border hover:bg-card/60 hover:text-foreground",
        className
      )}
    >
      {children}
    </button>
  );
}

export function BtnPrimary({
  children,
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      className={cn(
        "btn-primary w-full rounded-lg py-3 text-sm font-semibold text-white shadow-md shadow-primary/25 transition hover:brightness-110 disabled:opacity-50",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
