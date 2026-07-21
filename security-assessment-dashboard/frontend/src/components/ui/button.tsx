import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { type ButtonHTMLAttributes, forwardRef } from "react";

import { cn } from "@/utils/cn";

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium tracking-normal transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/70 disabled:pointer-events-none disabled:opacity-45",
  {
    variants: {
      variant: {
        default:
          "border border-primary/40 bg-primary text-primary-foreground shadow-[0_12px_32px_-16px_hsl(var(--primary))] hover:-translate-y-0.5 hover:bg-primary/90 hover:shadow-[0_18px_40px_-18px_hsl(var(--primary))]",
        outline:
          "border border-border/80 bg-card/70 text-foreground shadow-[inset_0_1px_0_hsl(var(--foreground)/0.04)] hover:-translate-y-0.5 hover:border-border hover:bg-secondary",
        ghost:
          "text-muted-foreground hover:bg-secondary/80 hover:text-foreground",
        destructive:
          "border border-destructive/40 bg-destructive/90 text-destructive-foreground shadow-[0_12px_32px_-18px_hsl(var(--destructive))] hover:-translate-y-0.5 hover:bg-destructive",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 rounded-lg px-3 text-xs",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
    );
  },
);
Button.displayName = "Button";
