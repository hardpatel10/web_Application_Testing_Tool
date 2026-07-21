import type { ReactNode } from "react";

import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface ChartCardProps {
  title: string;
  description?: string;
  action?: ReactNode;
  isEmpty?: boolean;
  emptyMessage?: string;
  children: ReactNode;
  className?: string;
}

/** Shared frame for every dashboard chart: title/description, an optional action, and an honest empty note. */
export function ChartCard({ title, description, action, isEmpty, emptyMessage, children, className }: ChartCardProps) {
  return (
    <Card className={className}>
      <CardHeader className="flex-row items-start justify-between gap-4 pb-2">
        <div>
          <CardTitle>{title}</CardTitle>
          {description && <CardDescription className="mt-1">{description}</CardDescription>}
        </div>
        {action}
      </CardHeader>
      <div className="px-6 pb-6">
        {isEmpty ? (
          <div className="flex h-[220px] items-center justify-center rounded-xl border border-dashed border-border/60 bg-secondary/20 px-6 text-center text-sm leading-6 text-muted-foreground">
            {emptyMessage ?? "No data collected yet."}
          </div>
        ) : (
          children
        )}
      </div>
    </Card>
  );
}
