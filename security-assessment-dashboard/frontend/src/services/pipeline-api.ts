import { apiGet, apiPost } from "@/services/api-client";
import type { PipelineRun, PipelineStartRequestPayload } from "@/types/pipeline";

export const pipelineApi = {
  start: (assessmentId: string, payload: PipelineStartRequestPayload) =>
    apiPost<PipelineRun>(`/assessments/${assessmentId}/pipeline/start`, payload),
  get: (assessmentId: string) => apiGet<PipelineRun>(`/assessments/${assessmentId}/pipeline`),
};
