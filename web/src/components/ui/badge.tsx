import { cn } from "@/lib/utils";

export function Badge({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border border-border/60 bg-background/50 px-2 py-0.5 text-xs font-medium shadow-inner-glow backdrop-blur-sm",
        className
      )}
    >
      {children}
    </span>
  );
}
