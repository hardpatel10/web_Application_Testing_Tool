import { useQuery } from "@tanstack/react-query";

import { scanProfilesApi } from "@/services/scan-profiles-api";
import type { ScanProfileListParams } from "@/types/scan-profile";

export const profileKeys = {
  all: ["scan-profiles"] as const,
  list: (toolName: string, params?: ScanProfileListParams) => [...profileKeys.all, toolName, params ?? {}] as const,
};

export function useScanProfiles(toolName: string, params?: ScanProfileListParams, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: profileKeys.list(toolName, params),
    queryFn: () => scanProfilesApi.list(toolName, params),
    enabled: options?.enabled ?? true,
  });
}
