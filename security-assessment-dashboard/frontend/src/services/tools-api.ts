import { apiGet, apiPost, apiPut } from "@/services/api-client";
import type {
  FilesystemBrowseResult,
  ToolConfigurationUpdate,
  ToolDetail,
  ToolDiagnostics,
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
  diagnostics: (name: string) => apiGet<ToolDiagnostics>(`${BASE}/${name}/diagnostics`),
  discover: () => apiPost<ToolDiscoveryResult>(`${BASE}/discover`),
  validate: (name?: string) => apiPost<ToolValidationResult[]>(`${BASE}/validate`, { name: name ?? null }),
  validateOne: (name: string) => apiPost<ToolValidationResult>(`${BASE}/${name}/validate`),
  checkHealth: (name: string) => apiPost<ToolHealthResult>(`${BASE}/${name}/health`),
  refresh: (name: string) => apiPost<ToolDetail>(`${BASE}/${name}/refresh`),
  updateConfiguration: (name: string, payload: ToolConfigurationUpdate) =>
    apiPut<ToolDetail>(`${BASE}/${name}/configuration`, payload),
  browseFilesystem: (path?: string) => apiGet<FilesystemBrowseResult>(`${BASE}/browse-filesystem`, { path }),
};
