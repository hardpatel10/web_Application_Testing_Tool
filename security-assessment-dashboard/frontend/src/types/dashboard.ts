import type { HostSummary } from "@/types/host-inventory";
import type { FindingSummary } from "@/types/finding";

export interface OverviewStats {
  assessments: number;
  targets: number;
  hosts_discovered: number;
  services: number;
  technologies: number;
  observations: number;
  findings: number;
  reports: number;
}

export interface SeverityCounts {
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

export interface ExecutionSummary {
  completed: number;
  running: number;
  failed: number;
  cancelled: number;
  average_duration_seconds: number | null;
}

export interface CountItem {
  label: string;
  count: number;
}

export interface TrendPoint {
  date: string;
  count: number;
}

export interface HostSummaryStats {
  hosts: number;
  operating_systems: number;
  technologies: number;
  services: number;
  top_open_ports: CountItem[];
  top_technologies: CountItem[];
}

export interface FindingDashboardStats {
  by_severity: CountItem[];
  by_category: CountItem[];
  by_plugin: CountItem[];
  by_host: CountItem[];
  newest: FindingSummary[];
  open_count: number;
  resolved_count: number;
}

export interface HostDashboardStats {
  newest: HostSummary[];
  most_active: CountItem[];
  operating_systems: CountItem[];
  technology_distribution: CountItem[];
  service_distribution: CountItem[];
}

export interface ChartSeries {
  execution_timeline: TrendPoint[];
  observation_trend: TrendPoint[];
  finding_trend: TrendPoint[];
  host_growth: TrendPoint[];
}

export interface Dashboard {
  is_empty: boolean;
  overview: OverviewStats;
  security_summary: SeverityCounts;
  execution_summary: ExecutionSummary;
  host_summary: HostSummaryStats;
  finding_dashboard: FindingDashboardStats;
  host_dashboard: HostDashboardStats;
  charts: ChartSeries;
}

export interface Statistics {
  overview: OverviewStats;
  security_summary: SeverityCounts;
  execution_summary: ExecutionSummary;
}
