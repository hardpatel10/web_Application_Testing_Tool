export type JobStatus =
  | "pending"
  | "queued"
  | "preparing"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "timeout"
  | "skipped";

export const ACTIVE_JOB_STATUSES: JobStatus[] = ["pending", "queued", "preparing", "running"];
export const RETRIABLE_JOB_STATUSES: JobStatus[] = ["failed", "cancelled", "timeout"];

export interface Job {
  id: string;
  assessment_id: string;
  target_id: string;
  target_value: string;
  tool_id: string;
  tool_name: string;
  status: JobStatus;
  status_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration: number | null;
  return_code: number | null;
  retry_count: number;
  log_path: string | null;
  profile_id: string | null;
  generated_command: string[] | null;
  created_at: string;
}

export interface ToolExecutionOptionsPayload {
  profile_id?: string | null;
  advanced_options?: Record<string, unknown> | null;
}

export interface ExecuteRequestPayload {
  tool_names: string[];
  target_ids?: string[] | null;
  tool_options?: Record<string, ToolExecutionOptionsPayload> | null;
}

export interface ServiceResult {
  id: string;
  port: number;
  protocol: string;
  state: string;
  service_name: string | null;
  product: string | null;
  version: string | null;
  extra_info: string | null;
}

export interface HostResult {
  id: string;
  ip_address: string | null;
  hostname: string | null;
  mac_address: string | null;
  mac_vendor: string | null;
  state: string;
  os_name: string | null;
  os_accuracy: number | null;
  services: ServiceResult[];
}

export interface ObservationResult {
  id: string;
  host_id: string | null;
  port: number | null;
  source: string;
  title: string;
  detail: string | null;
}

export interface JobResultsResult {
  job_id: string;
  hosts: HostResult[];
  observations: ObservationResult[];
}

export interface RawOutputResult {
  job_id: string;
  format: string;
  content: string | null;
  created_at: string;
}

export interface ExecuteResult {
  assessment_id: string;
  jobs: Job[];
  queued_count: number;
  skipped_count: number;
}

export interface JobLogsResult {
  job_id: string;
  lines: string[];
  log_path: string | null;
}

export interface AssessmentProgress {
  assessment_id: string;
  total: number;
  pending: number;
  queued: number;
  preparing: number;
  running: number;
  completed: number;
  failed: number;
  cancelled: number;
  timeout: number;
  skipped: number;
  percent_complete: number;
  current_jobs: Job[];
}

export interface JobListParams {
  assessment_id?: string;
  status?: JobStatus;
  tool_name?: string;
  target_id?: string;
  sort_by?: string;
  sort_desc?: boolean;
}

export const JOB_STATUS_OPTIONS: { value: JobStatus; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "queued", label: "Queued" },
  { value: "preparing", label: "Preparing" },
  { value: "running", label: "Running" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "timeout", label: "Timeout" },
  { value: "skipped", label: "Skipped" },
];
