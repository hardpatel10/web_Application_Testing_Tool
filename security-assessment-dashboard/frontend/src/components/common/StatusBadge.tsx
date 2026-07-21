import { Badge, type BadgeProps } from "@/components/ui/badge";
import type { AssessmentStatus } from "@/types/assessment";

const STATUS_VARIANT: Record<AssessmentStatus, NonNullable<BadgeProps["variant"]>> = {
  draft: "secondary",
  ready: "outline",
  running: "success",
  paused: "warning",
  completed: "success",
  cancelled: "destructive",
  archived: "secondary",
};

export function StatusBadge({ status }: { status: AssessmentStatus }) {
  return (
    <Badge variant={STATUS_VARIANT[status]} className="capitalize">
      {status.replace("_", " ")}
    </Badge>
  );
}
