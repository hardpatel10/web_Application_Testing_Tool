import { apiDelete, apiGet, apiPost, apiPut } from "@/services/api-client";
import type {
  CommandPreviewRequest,
  CommandPreviewResponse,
  ScanProfile,
  ScanProfileDuplicateRequest,
  ScanProfileImportRequest,
  ScanProfileListParams,
  ScanProfileWrite,
} from "@/types/scan-profile";

const base = (toolName: string) => `/tools/${toolName}/profiles`;

export const scanProfilesApi = {
  list: (toolName: string, params?: ScanProfileListParams) =>
    apiGet<ScanProfile[]>(base(toolName), params as Record<string, unknown>),
  get: (toolName: string, profileId: string) => apiGet<ScanProfile>(`${base(toolName)}/${profileId}`),
  create: (toolName: string, payload: ScanProfileWrite) => apiPost<ScanProfile>(base(toolName), payload),
  update: (toolName: string, profileId: string, payload: ScanProfileWrite) =>
    apiPut<ScanProfile>(`${base(toolName)}/${profileId}`, payload),
  delete: (toolName: string, profileId: string) => apiDelete<void>(`${base(toolName)}/${profileId}`),
  duplicate: (toolName: string, profileId: string, payload: ScanProfileDuplicateRequest) =>
    apiPost<ScanProfile>(`${base(toolName)}/${profileId}/duplicate`, payload),
  import: (toolName: string, payload: ScanProfileImportRequest) =>
    apiPost<ScanProfile>(`${base(toolName)}/import`, payload),
  export: (toolName: string, profileId: string) => apiGet<Record<string, unknown>>(`${base(toolName)}/${profileId}/export`),
  enable: (toolName: string, profileId: string) => apiPost<ScanProfile>(`${base(toolName)}/${profileId}/enable`),
  disable: (toolName: string, profileId: string) => apiPost<ScanProfile>(`${base(toolName)}/${profileId}/disable`),
  previewCommand: (toolName: string, payload: CommandPreviewRequest) =>
    apiPost<CommandPreviewResponse>(`${base(toolName)}/preview-command`, payload),
};
