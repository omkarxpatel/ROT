"use client";

import { AlertTriangle, Info, Lightbulb, Quote } from "lucide-react";

import { cn } from "@/lib/utils";

type CalloutVariant = "note" | "warning" | "tip" | "context";

interface CalloutProps {
  variant?: CalloutVariant;
  title?: string;
  children: React.ReactNode;
}

const VARIANTS: Record<
  CalloutVariant,
  {
    icon: React.ComponentType<{ className?: string }>;
    border: string;
    bg: string;
    title: string;
    accent: string;
    defaultTitle: string;
  }
> = {
  note: {
    icon: Info,
    border: "border-sky-500/30",
    bg: "bg-sky-500/5",
    title: "text-sky-300",
    accent: "text-sky-300",
    defaultTitle: "Note",
  },
  warning: {
    icon: AlertTriangle,
    border: "border-amber-500/30",
    bg: "bg-amber-500/5",
    title: "text-amber-300",
    accent: "text-amber-300",
    defaultTitle: "Watch out",
  },
  tip: {
    icon: Lightbulb,
    border: "border-emerald-500/30",
    bg: "bg-emerald-500/5",
    title: "text-emerald-300",
    accent: "text-emerald-300",
    defaultTitle: "Tip",
  },
  context: {
    icon: Quote,
    border: "border-violet-500/30",
    bg: "bg-violet-500/5",
    title: "text-violet-300",
    accent: "text-violet-300",
    defaultTitle: "Under the hood",
  },
};

export function Callout({
  variant = "note",
  title,
  children,
}: CalloutProps) {
  const config = VARIANTS[variant];
  const Icon = config.icon;
  return (
    <div
      className={cn(
        "my-5 overflow-hidden rounded-lg border px-4 py-3",
        config.border,
        config.bg,
      )}
    >
      <div className="flex items-center gap-2">
        <Icon className={cn("h-4 w-4", config.accent)} />
        <span
          className={cn(
            "text-[11px] font-semibold uppercase tracking-wider",
            config.title,
          )}
        >
          {title ?? config.defaultTitle}
        </span>
      </div>
      <div className="mt-2 space-y-2 text-[13.5px] leading-relaxed text-foreground/85 [&>p]:m-0 [&>p+p]:mt-2 [&_code]:rounded [&_code]:bg-background/40 [&_code]:px-1 [&_code]:py-[1px] [&_code]:font-mono [&_code]:text-[12px]">
        {children}
      </div>
    </div>
  );
}
