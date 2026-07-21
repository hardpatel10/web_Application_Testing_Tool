export type AssessmentStatus = "draft" | "ready" | "running" | "paused" | "completed" | "cancelled" | "archived";

export type AssessmentType = "network" | "web_application" | "api" | "mobile" | "cloud" | "internal" | "external" | "custom";

export type AssessmentHistoryEventType =
  | "created"
  | "updated"
  | "status_changed"
  | "archived"
  | "restored"
  | "deleted"
  | "duplicated"
  | "target_added"
  | "target_updated"
  | "target_removed"
  | "targets_imported";

export interface Assessment {
  id: string;
  name: string;
  description: string | null;
  assessment_type: AssessmentType;
  status: AssessmentStatus;
  tags: string[];
  target_count: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AssessmentCreatePayload {
  name: string;
  description?: string | null;
  assessment_type: AssessmentType;
  tags?: string[];
}

export interface AssessmentUpdatePayload {
  name?: string;
  description?: string | null;
  assessment_type?: AssessmentType;
  status?: AssessmentStatus;
  tags?: string[];
  started_at?: string | null;
  completed_at?: string | null;
}

export interface AssessmentHistoryEntry {
  id: string;
  event_type: AssessmentHistoryEventType;
  message: string;
  created_at: string;
}

export const ASSESSMENT_TYPE_OPTIONS: { value: AssessmentType; label: string }[] = [
  { value: "network", label: "Network Assessment" },
  { value: "web_application", label: "Web Application" },
  { value: "api", label: "API Assessment" },
  { value: "mobile", label: "Mobile Assessment" },
  { value: "cloud", label: "Cloud Assessment" },
  { value: "internal", label: "Internal Assessment" },
  { value: "external", label: "External Assessment" },
  { value: "custom", label: "Custom" },
];

export const ASSESSMENT_STATUS_OPTIONS: { value: AssessmentStatus; label: string }[] = [
  { value: "draft", label: "Draft" },
  { value: "ready", label: "Ready" },
  { value: "running", label: "Running" },
  { value: "paused", label: "Paused" },
  { value: "completed", label: "Completed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "archived", label: "Archived" },
];

export interface AssessmentListParams {
  search?: string;
  status?: AssessmentStatus;
  assessment_type?: AssessmentType;
  tags?: string[];
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}
