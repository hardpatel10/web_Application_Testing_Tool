import { apiDelete, apiGet, apiPost, apiPut } from "@/services/api-client";
import type {
  Assessment,
  AssessmentCreatePayload,
  AssessmentHistoryEntry,
  AssessmentListParams,
  AssessmentUpdatePayload,
} from "@/types/assessment";
import type { PageResponse } from "@/types/pagination";

const BASE = "/assessments";

export const assessmentsApi = {
  list: (params: AssessmentListParams) => apiGet<PageResponse<Assessment>>(BASE, params as Record<string, unknown>),
  get: (id: string) => apiGet<Assessment>(`${BASE}/${id}`),
  create: (payload: AssessmentCreatePayload) => apiPost<Assessment>(BASE, payload),
  update: (id: string, payload: AssessmentUpdatePayload) => apiPut<Assessment>(`${BASE}/${id}`, payload),
  remove: (id: string) => apiDelete<void>(`${BASE}/${id}`),
  archive: (id: string) => apiPost<Assessment>(`${BASE}/${id}/archive`),
  restore: (id: string) => apiPost<Assessment>(`${BASE}/${id}/restore`),
  duplicate: (id: string, name?: string) => apiPost<Assessment>(`${BASE}/${id}/duplicate`, { name: name ?? null }),
  history: (id: string, page = 1, pageSize = 50) =>
    apiGet<PageResponse<AssessmentHistoryEntry>>(`${BASE}/${id}/history`, { page, page_size: pageSize }),
};
