import { Badge, type BadgeProps } from "@/components/ui/badge";
import type { JobStatus } from "@/types/execution";

const STATUS_VARIANT: Record<JobStatus, NonNullable<BadgeProps["variant"]>> = {
  pending: "secondary",
  queued: "outline",
  preparing: "outline",
  running: "default",
  completed: "success",
  failed: "destructive",
  cancelled: "destructive",
  timeout: "warning",
  skipped: "secondary",
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  return (
    <Badge variant={STATUS_VARIANT[status]} className="capitalize">
      {status}
    </Badge>
  );
}
