export type PipelineStage = "recon" | "scan" | "correlate";

export type PipelineJobStatus = "waiting" | "running" | "skipped" | "completed" | "failed";

export type PipelineRunStatus = "running" | "completed" | "failed";

export interface PipelineJob {
  id: string;
  stage: PipelineStage;
  tool_name: string | null;
  host_id: string | null;
  host_label: string | null;
  service_id: string | null;
  execution_id: string | null;
  target_value: string | null;
  status: PipelineJobStatus;
  skip_reason: string | null;
  created_at: string;
}

export interface PipelineRun {
  id: string;
  assessment_id: string;
  recon_execution_id: string | null;
  status: PipelineRunStatus;
  started_at: string;
  completed_at: string | null;
  jobs: PipelineJob[];
}

export interface PipelineStartRequestPayload {
  target_id: string;
}
