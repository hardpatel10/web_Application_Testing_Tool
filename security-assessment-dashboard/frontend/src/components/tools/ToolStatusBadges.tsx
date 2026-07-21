import { Badge } from "@/components/ui/badge";
import type { ToolHealthStatus, ToolStatus } from "@/types/tool";

const STATUS_VARIANT: Record<ToolStatus, "success" | "secondary" | "warning" | "destructive"> = {
  installed: "success",
  missing: "secondary",
  disabled: "secondary",
  misconfigured: "warning",
  unsupported_version: "destructive",
};

const STATUS_LABEL: Record<ToolStatus, string> = {
  installed: "Installed",
  missing: "Missing",
  disabled: "Disabled",
  misconfigured: "Misconfigured",
  unsupported_version: "Unsupported Version",
};

export function ToolStatusBadge({ status }: { status: ToolStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{STATUS_LABEL[status]}</Badge>;
}

const HEALTH_VARIANT: Record<ToolHealthStatus, "success" | "warning" | "destructive"> = {
  healthy: "success",
  warning: "warning",
  error: "destructive",
};

const HEALTH_LABEL: Record<ToolHealthStatus, string> = {
  healthy: "Healthy",
  warning: "Warning",
  error: "Error",
};

export function ToolHealthBadge({ health }: { health: ToolHealthStatus | null }) {
  if (!health) {
    return <Badge variant="secondary">Not checked</Badge>;
  }
  return <Badge variant={HEALTH_VARIANT[health]}>{HEALTH_LABEL[health]}</Badge>;
}
