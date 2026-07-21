import { apiGet } from "@/services/api-client";
import type { ScanProfile, ScanProfileListParams } from "@/types/scan-profile";

const base = (toolName: string) => `/tools/${toolName}/profiles`;

export const scanProfilesApi = {
  list: (toolName: string, params?: ScanProfileListParams) =>
    apiGet<ScanProfile[]>(base(toolName), params as Record<string, unknown>),
};
