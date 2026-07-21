import { apiGet, apiPost, apiPut } from "@/services/api-client";
import type {
  FilesystemBrowseResult,
  ToolConfigurationUpdate,
  ToolDetail,
  ToolDiscoveryResult,
  ToolHealthResult,
  ToolListParams,
  ToolSummary,
  ToolValidationResult,
} from "@/types/tool";

const BASE = "/tools";

export const toolsApi = {
  list: (params?: ToolListParams) => apiGet<ToolSummary[]>(BASE, params as Record<string, unknown>),
  get: (name: string) => apiGet<ToolDetail>(`${BASE}/${name}`),
  discover: () => apiPost<ToolDiscoveryResult>(`${BASE}/discover`),
  validate: (name?: string) => apiPost<ToolValidationResult[]>(`${BASE}/validate`, { name: name ?? null }),
  checkHealth: (name: string) => apiPost<ToolHealthResult>(`${BASE}/${name}/health`),
  updateConfiguration: (name: string, payload: ToolConfigurationUpdate) =>
    apiPut<ToolDetail>(`${BASE}/${name}/configuration`, payload),
  browseFilesystem: (path?: string) => apiGet<FilesystemBrowseResult>(`${BASE}/browse-filesystem`, { path }),
};
