import { apiDelete, apiDownload, apiGet, apiPost, apiPostForm, apiPut } from "@/services/api-client";
import type {
  Target,
  TargetBulkImportResult,
  TargetCreatePayload,
  TargetListParams,
  TargetType,
  TargetUpdatePayload,
  TargetValidateResult,
} from "@/types/target";
import type { PageResponse } from "@/types/pagination";

const base = (assessmentId: string) => `/assessments/${assessmentId}/targets`;

export const targetsApi = {
  list: (assessmentId: string, params: TargetListParams) =>
    apiGet<PageResponse<Target>>(base(assessmentId), params as Record<string, unknown>),
  create: (assessmentId: string, payload: TargetCreatePayload) => apiPost<Target>(base(assessmentId), payload),
  update: (assessmentId: string, targetId: string, payload: TargetUpdatePayload) =>
    apiPut<Target>(`${base(assessmentId)}/${targetId}`, payload),
  remove: (assessmentId: string, targetId: string) => apiDelete<void>(`${base(assessmentId)}/${targetId}`),
  enable: (assessmentId: string, targetId: string) => apiPost<Target>(`${base(assessmentId)}/${targetId}/enable`),
  disable: (assessmentId: string, targetId: string) => apiPost<Target>(`${base(assessmentId)}/${targetId}/disable`),
  duplicate: (assessmentId: string, targetId: string, targetValue?: string) =>
    apiPost<Target>(`${base(assessmentId)}/${targetId}/duplicate`, { target_value: targetValue ?? null }),
  validate: (assessmentId: string, targetType: TargetType, targetValue: string) =>
    apiPost<TargetValidateResult>(`${base(assessmentId)}/validate`, { target_type: targetType, target_value: targetValue }),
  bulkImport: (assessmentId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiPostForm<TargetBulkImportResult>(`${base(assessmentId)}/bulk-import`, form);
  },
};

export async function downloadTargets(assessmentId: string, format: "txt" | "csv"): Promise<void> {
  const blob = await apiDownload(`${base(assessmentId)}/export`, { format });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `targets.${format}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
