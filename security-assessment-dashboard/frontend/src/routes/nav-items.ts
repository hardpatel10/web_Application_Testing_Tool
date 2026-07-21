import {
  ClipboardList,
  Eye,
  FileBarChart,
  LayoutDashboard,
  Layers,
  MonitorSmartphone,
  Network,
  PlayCircle,
  Server,
  Settings,
  ShieldAlert,
  Wrench,
} from "lucide-react";

import type { NavItem } from "@/types/navigation";

export const navItems: NavItem[] = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard },
  { label: "Assessments", path: "/assessments", icon: ClipboardList },
  { label: "Tools", path: "/tools", icon: Wrench },
  { label: "Executions", path: "/executions", icon: PlayCircle },
  { label: "Findings", path: "/findings", icon: ShieldAlert },
  { label: "Security Overview", path: "/security-overview", icon: ShieldAlert },
  { label: "Hosts", path: "/hosts", icon: Server },
  { label: "Host Overview", path: "/host-overview", icon: Server },
  { label: "Services", path: "/services", icon: Network },
  { label: "Technologies", path: "/technologies", icon: Layers },
  { label: "Technology Overview", path: "/technology-overview", icon: Layers },
  { label: "Observations", path: "/observations", icon: Eye },
  { label: "Operating Systems", path: "/operating-systems", icon: MonitorSmartphone },
  { label: "Reports", path: "/reports", icon: FileBarChart },
  { label: "Settings", path: "/settings", icon: Settings },
];
