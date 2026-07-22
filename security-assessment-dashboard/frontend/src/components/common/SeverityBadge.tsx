import { AlertCircle, AlertOctagon, AlertTriangle, Info, MinusCircle } from "lucide-react";

import { SEVERITY_COLOR } from "@/utils/chart-palette";

const SEVERITY_ICON = {
  critical: AlertOctagon,
  high: AlertTriangle,
  medium: AlertCircle,
  low: MinusCircle,
  info: Info,
} as const;

type Severity = keyof typeof SEVERITY_ICON;

/**
 * A finding's severity: icon + label, never color alone (a status color is never
 * the sole carrier of meaning -- see the dataviz skill's status-palette rule).
 */
export function SeverityBadge({ severity, className }: { severity: string; className?: string }) {
  const key = (severity in SEVERITY_ICON ? severity : "info") as Severity;
  const color = SEVERITY_COLOR[key];
  const Icon = SEVERITY_ICON[key];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium capitalize leading-none shadow-[inset_0_1px_0_rgba(255,255,255,0.035)] ${className ?? ""}`}
      style={{ borderColor: `${color}40`, backgroundColor: `${color}1a`, color }}
    >
      <Icon className="h-3.5 w-3.5" />
      {key}
    </span>
  );
}
