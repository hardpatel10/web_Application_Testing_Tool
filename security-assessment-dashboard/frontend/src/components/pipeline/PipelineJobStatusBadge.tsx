import { Badge, type BadgeProps } from "@/components/ui/badge";
import type { PipelineJobStatus } from "@/types/pipeline";

const STATUS_VARIANT: Record<PipelineJobStatus, NonNullable<BadgeProps["variant"]>> = {
  waiting: "outline",
  running: "default",
  completed: "success",
  failed: "destructive",
  skipped: "secondary",
};

export function PipelineJobStatusBadge({ status }: { status: PipelineJobStatus }) {
  return (
    <Badge variant={STATUS_VARIANT[status]} className="capitalize">
      {status}
    </Badge>
  );
}
