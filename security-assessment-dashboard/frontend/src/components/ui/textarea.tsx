import { type TextareaHTMLAttributes, forwardRef } from "react";

import { cn } from "@/utils/cn";

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "flex min-h-[96px] w-full rounded-xl border border-input/80 bg-background/40 px-3 py-2.5 text-sm leading-6 text-foreground shadow-[inset_0_1px_0_hsl(var(--foreground)/0.035)] transition-all",
        "placeholder:text-muted-foreground/80 hover:border-border focus-visible:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/25",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";
