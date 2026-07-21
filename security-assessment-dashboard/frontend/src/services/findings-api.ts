import { apiGet, apiPost } from "@/services/api-client";
import type {
  CorrelationRunResult,
  CorrelationStatus,
  FindingDetail,
  FindingListParams,
  FindingSummary,
} from "@/types/finding";
import type { PageResponse } from "@/types/pagination";

export const findingsApi = {
  list: (params?: FindingListParams) => apiGet<PageResponse<FindingSummary>>("/findings", params as Record<string, unknown>),
  get: (id: string) => apiGet<FindingDetail>(`/findings/${id}`),
};

export const correlationApi = {
  run: (assessmentId?: string) => apiPost<CorrelationRunResult>("/correlation/run", { assessment_id: assessmentId ?? null }),
  status: () => apiGet<CorrelationStatus>("/correlation/status"),
};
