"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import {
  SectionCard,
  type SectionCardVariant,
  SectionCardHeader,
} from "@/components/ui/section-card";

type Props = {
  title: string;
  subtitle?: string;
  variant?: SectionCardVariant;
  className?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
};

function Chevron({ open }: { open: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex h-7 w-7 items-center justify-center rounded-md border border-border-bright text-muted transition-transform",
        open && "rotate-180"
      )}
      aria-hidden
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M6 9l6 6 6-6" />
      </svg>
    </span>
  );
}

export function CollapsibleSectionCard({
  title,
  subtitle,
  variant = "muted",
  className,
  defaultOpen = false,
  children,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <SectionCard variant={variant} className={className}>
      <button
        type="button"
        className="block w-full text-left"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <SectionCardHeader
          title={title}
          subtitle={subtitle ?? "点击展开"}
          className={cn("mb-0", open && "mb-5")}
          action={<Chevron open={open} />}
        />
      </button>
      {open ? <div>{children}</div> : null}
    </SectionCard>
  );
}
