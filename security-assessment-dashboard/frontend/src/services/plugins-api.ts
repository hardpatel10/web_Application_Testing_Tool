import { apiGet, apiPost } from "@/services/api-client";
import type {
  PluginDetail,
  PluginHealth,
  PluginReloadResult,
  PluginSummary,
  PluginValidationResult,
} from "@/types/plugin";

const BASE = "/plugins";

export const pluginsApi = {
  list: () => apiGet<PluginSummary[]>(BASE),
  get: (id: string) => apiGet<PluginDetail>(`${BASE}/${id}`),
  health: (id: string) => apiGet<PluginHealth>(`${BASE}/${id}/health`),
  validate: (id: string) => apiGet<PluginValidationResult>(`${BASE}/${id}/validate`),
  reload: () => apiPost<PluginReloadResult>(`${BASE}/reload`),
};
