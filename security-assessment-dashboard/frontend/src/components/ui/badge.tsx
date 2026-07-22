import { cva, type VariantProps } from "class-variance-authority";
import { type HTMLAttributes } from "react";

import { cn } from "@/utils/cn";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium leading-none shadow-[inset_0_1px_0_hsl(var(--foreground)/0.035)] transition-colors focus:outline-none focus:ring-2 focus:ring-ring/60",
  {
    variants: {
      variant: {
        default: "border-primary/30 bg-primary/15 text-blue-200",
        secondary: "border-border/70 bg-secondary/70 text-muted-foreground",
        outline: "border-border/80 bg-background/35 text-foreground",
        success: "border-emerald-400/25 bg-emerald-500/10 text-emerald-300",
        warning: "border-amber-400/25 bg-amber-500/10 text-amber-300",
        destructive: "border-destructive/30 bg-destructive/10 text-red-300",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}
