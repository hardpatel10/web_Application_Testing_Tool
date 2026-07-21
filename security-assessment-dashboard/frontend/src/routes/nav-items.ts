import { ClipboardList, FileBarChart, LayoutDashboard, PlayCircle, Settings, ShieldAlert, Wrench } from "lucide-react";

import type { NavItem } from "@/types/navigation";

/**
 * The application revolves around these seven concepts only -- internal inventory concepts
 * (hosts/services/technologies/observations/operating systems) are never standalone nav
 * destinations. That data is still fully available, just contextually: inside an Assessment's
 * "Assets Discovered" tab, an Execution's results, or a Finding's supporting evidence.
 */
export const navItems: NavItem[] = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard },
  { label: "Assessments", path: "/assessments", icon: ClipboardList },
  { label: "Tools", path: "/tools", icon: Wrench },
  { label: "Executions", path: "/executions", icon: PlayCircle },
  { label: "Findings", path: "/findings", icon: ShieldAlert },
  { label: "Reports", path: "/reports", icon: FileBarChart },
  { label: "Settings", path: "/settings", icon: Settings },
];
