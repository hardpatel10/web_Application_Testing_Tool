import { apiGet, apiPost } from "@/services/api-client";
import type {
  AssessmentProgress,
  ExecuteRequestPayload,
  ExecuteResult,
  Job,
  JobListParams,
  JobLogsResult,
  JobResultsResult,
  RawOutputResult,
} from "@/types/execution";

export const executionsApi = {
  execute: (assessmentId: string, payload: ExecuteRequestPayload) =>
    apiPost<ExecuteResult>(`/assessments/${assessmentId}/execute`, payload),
  progress: (assessmentId: string) => apiGet<AssessmentProgress>(`/assessments/${assessmentId}/progress`),
  listJobs: (params?: JobListParams) => apiGet<Job[]>("/jobs", params as Record<string, unknown>),
  getJob: (jobId: string) => apiGet<Job>(`/jobs/${jobId}`),
  getLogs: (jobId: string, params?: { tail?: number; search?: string }) =>
    apiGet<JobLogsResult>(`/jobs/${jobId}/logs`, params as Record<string, unknown>),
  getResults: (jobId: string) => apiGet<JobResultsResult>(`/jobs/${jobId}/results`),
  getRawOutput: (jobId: string) => apiGet<RawOutputResult>(`/jobs/${jobId}/raw-output`),
  cancelJob: (jobId: string) => apiPost<Job>(`/jobs/${jobId}/cancel`),
  retryJob: (jobId: string) => apiPost<Job>(`/jobs/${jobId}/retry`),
};
