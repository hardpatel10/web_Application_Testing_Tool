import { type HTMLAttributes } from "react";

import { cn } from "@/utils/cn";

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("animate-pulse rounded-xl bg-secondary/70", className)} {...props} />;
}
