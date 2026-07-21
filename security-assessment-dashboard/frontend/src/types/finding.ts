import type { ExecutionHistoryEntry, HostSummary, Observation, Service } from "@/types/host-inventory";

export type FindingSeverity = "critical" | "high" | "medium" | "low" | "info";
export type FindingConfidence = "confirmed" | "high" | "medium" | "low";
export type FindingStatus = "open" | "confirmed" | "false_positive" | "accepted_risk" | "remediated" | "duplicate";
export type FindingReferenceType = "cwe" | "owasp" | "capec" | "cve" | "vendor_url" | "documentation_url";

export const FINDING_SEVERITY_OPTIONS: { value: FindingSeverity; label: string }[] = [
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
  { value: "info", label: "Informational" },
];

export const FINDING_CONFIDENCE_OPTIONS: { value: FindingConfidence; label: string }[] = [
  { value: "confirmed", label: "Confirmed" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

export const FINDING_STATUS_OPTIONS: { value: FindingStatus; label: string }[] = [
  { value: "open", label: "Open" },
  { value: "confirmed", label: "Confirmed" },
  { value: "false_positive", label: "False Positive" },
  { value: "accepted_risk", label: "Accepted Risk" },
  { value: "remediated", label: "Remediated" },
  { value: "duplicate", label: "Duplicate" },
];

export const RESOLVED_FINDING_STATUSES: FindingStatus[] = ["remediated", "false_positive", "accepted_risk", "duplicate"];

export interface FindingReference {
  id: string;
  reference_type: FindingReferenceType;
  reference_value: string;
}

export interface FindingEvidence {
  id: string;
  source_tool: string;
  title: string | null;
  content: string | null;
  file_path: string | null;
  created_at: string;
}

export interface FindingSummary {
  id: string;
  assessment_id: string;
  host_id: string | null;
  rule_id: string;
  plugin: string | null;
  title: string;
  severity: FindingSeverity;
  confidence: FindingConfidence;
  category: string | null;
  status: FindingStatus;
  first_seen: string;
  last_seen: string;
  host_label: string | null;
  evidence_count: number;
  observation_count: number;
}

export interface FindingDetail {
  id: string;
  assessment_id: string;
  host_id: string | null;
  source_execution_id: string | null;
  rule_id: string;
  plugin: string | null;
  title: string;
  description: string | null;
  impact: string | null;
  severity: FindingSeverity;
  confidence: FindingConfidence;
  category: string | null;
  cvss_score: number | null;
  cwe: string | null;
  owasp: string | null;
  remediation: string | null;
  status: FindingStatus;
  first_seen: string;
  last_seen: string;
  created_at: string;
  updated_at: string;
  host: HostSummary | null;
  affected_services: Service[];
  supporting_observations: Observation[];
  evidence: FindingEvidence[];
  references: FindingReference[];
  execution_history: ExecutionHistoryEntry[];
}

export interface FindingListParams {
  assessment_id?: string;
  host_id?: string;
  severity?: FindingSeverity;
  confidence?: FindingConfidence;
  status?: FindingStatus;
  category?: string;
  plugin?: string;
  rule_id?: string;
  search?: string;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export interface CorrelationRun {
  id: string;
  assessment_id: string | null;
  status: "running" | "completed" | "failed";
  started_at: string;
  completed_at: string | null;
  hosts_evaluated: number;
  rules_evaluated: number;
  findings_created: number;
  findings_updated: number;
  error_message: string | null;
}

export interface CorrelationRunResult {
  assessment_id: string | null;
  hosts_evaluated: number;
  rules_evaluated: number;
  rule_count: number;
  findings_created: number;
  findings_updated: number;
}

export interface CorrelationStatus {
  registered_rule_count: number;
  last_run: CorrelationRun | null;
  recent_runs: CorrelationRun[];
}
