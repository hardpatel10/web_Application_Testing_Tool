import type { ReactNode } from "react";
import { Sparkles } from "lucide-react";

import { Card } from "@/components/ui/card";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
  secondaryAction?: ReactNode;
  tip?: string;
  icon?: ReactNode;
}

export function EmptyState({ title, description, action, secondaryAction, tip, icon }: EmptyStateProps) {
  return (
    <Card className="overflow-hidden">
      <div className="relative flex min-h-[220px] flex-col items-start justify-center gap-5 p-8">
        <div className="absolute right-8 top-8 h-24 w-24 rounded-full border border-border/50 opacity-40" />
        <div className="absolute right-20 top-20 h-10 w-10 rounded-full border border-primary/30 opacity-50" />
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-border/70 bg-secondary/60 text-primary shadow-[inset_0_1px_0_hsl(var(--foreground)/0.05)]">
          {icon ?? <Sparkles className="h-5 w-5" />}
        </div>
        <div className="max-w-xl space-y-2">
          <h2 className="text-xl font-semibold tracking-normal text-foreground">{title}</h2>
          {description && <p className="text-sm leading-6 text-muted-foreground">{description}</p>}
        </div>
        {(action || secondaryAction) && (
          <div className="flex flex-wrap items-center gap-2">
            {action}
            {secondaryAction}
          </div>
        )}
        {tip && (
          <p className="max-w-xl rounded-xl border border-border/60 bg-secondary/35 px-3 py-2 text-xs leading-5 text-muted-foreground">
            {tip}
          </p>
        )}
      </div>
    </Card>
  );
}
