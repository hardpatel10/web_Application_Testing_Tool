import { AlertOctagon, AlertTriangle, CheckCircle2, CircleSlash, HelpCircle, XCircle } from "lucide-react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { TOOL_OVERALL_STATUS_LABELS, type ToolOverallStatus } from "@/types/tool";

const ICON: Record<ToolOverallStatus, typeof CheckCircle2> = {
  healthy: CheckCircle2,
  warning: AlertTriangle,
  error: XCircle,
  disabled: CircleSlash,
  unsupported_version: AlertOctagon,
  missing: HelpCircle,
};

const VARIANT: Record<ToolOverallStatus, BadgeProps["variant"]> = {
  healthy: "success",
  warning: "warning",
  error: "destructive",
  disabled: "secondary",
  unsupported_version: "destructive",
  missing: "secondary",
};

/**
 * The single, unified status badge for Tool Management -- collapses the backend's two
 * independent dimensions (lifecycle status + health) into the one answer a user actually
 * wants at a glance. Icon + label always together, never color alone (see SeverityBadge).
 */
export function ToolOverallStatusBadge({ status, className }: { status: ToolOverallStatus; className?: string }) {
  const Icon = ICON[status];
  return (
    <Badge variant={VARIANT[status]} className={`inline-flex items-center gap-1.5 ${className ?? ""}`}>
      <Icon className="h-3.5 w-3.5" /> {TOOL_OVERALL_STATUS_LABELS[status]}
    </Badge>
  );
}
