import type { ReactNode } from "react";

import { cn } from "@/utils/cn";

interface StatTileProps {
  label: string;
  value: number | string;
  icon?: ReactNode;
  accentClassName?: string;
}

function formatCompact(value: number): string {
  if (value < 1000) return String(value);
  if (value < 1_000_000) return `${(value / 1000).toFixed(value % 1000 === 0 ? 0 : 1)}K`;
  return `${(value / 1_000_000).toFixed(1)}M`;
}

/** A single KPI figure: sentence-case label, semibold proportional-figure value. */
export function StatTile({ label, value, icon, accentClassName }: StatTileProps) {
  const display = typeof value === "number" ? formatCompact(value) : value;
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-border/70 bg-secondary/25 px-4 py-3.5">
      {icon && (
        <div className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-border/70 bg-secondary/60 text-primary", accentClassName)}>
          {icon}
        </div>
      )}
      <div className="min-w-0">
        <p className="truncate text-xs text-muted-foreground">{label}</p>
        <p className="text-2xl font-semibold tracking-tight text-foreground">{display}</p>
      </div>
    </div>
  );
}
