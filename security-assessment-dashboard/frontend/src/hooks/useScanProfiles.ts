import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/services/api-client";
import { scanProfilesApi } from "@/services/scan-profiles-api";
import type {
  ScanProfileDuplicateRequest,
  ScanProfileImportRequest,
  ScanProfileListParams,
  ScanProfileWrite,
} from "@/types/scan-profile";

export const profileKeys = {
  all: ["scan-profiles"] as const,
  list: (toolName: string, params?: ScanProfileListParams) => [...profileKeys.all, toolName, params ?? {}] as const,
};

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong.";
}

export function useScanProfiles(toolName: string, params?: ScanProfileListParams, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: profileKeys.list(toolName, params),
    queryFn: () => scanProfilesApi.list(toolName, params),
    enabled: options?.enabled ?? true,
  });
}

function useInvalidateProfiles(toolName: string) {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: [...profileKeys.all, toolName] });
}

export function useCreateScanProfile(toolName: string) {
  const invalidate = useInvalidateProfiles(toolName);
  return useMutation({
    mutationFn: (payload: ScanProfileWrite) => scanProfilesApi.create(toolName, payload),
    onSuccess: () => {
      invalidate();
      toast.success("Scan Profile created.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useUpdateScanProfile(toolName: string) {
  const invalidate = useInvalidateProfiles(toolName);
  return useMutation({
    mutationFn: ({ profileId, payload }: { profileId: string; payload: ScanProfileWrite }) =>
      scanProfilesApi.update(toolName, profileId, payload),
    onSuccess: () => {
      invalidate();
      toast.success("Scan Profile updated.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useDeleteScanProfile(toolName: string) {
  const invalidate = useInvalidateProfiles(toolName);
  return useMutation({
    mutationFn: (profileId: string) => scanProfilesApi.delete(toolName, profileId),
    onSuccess: () => {
      invalidate();
      toast.success("Scan Profile deleted.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useDuplicateScanProfile(toolName: string) {
  const invalidate = useInvalidateProfiles(toolName);
  return useMutation({
    mutationFn: ({ profileId, payload }: { profileId: string; payload: ScanProfileDuplicateRequest }) =>
      scanProfilesApi.duplicate(toolName, profileId, payload),
    onSuccess: () => {
      invalidate();
      toast.success("Scan Profile duplicated.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useImportScanProfile(toolName: string) {
  const invalidate = useInvalidateProfiles(toolName);
  return useMutation({
    mutationFn: (payload: ScanProfileImportRequest) => scanProfilesApi.import(toolName, payload),
    onSuccess: () => {
      invalidate();
      toast.success("Scan Profile imported.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useExportScanProfile(toolName: string) {
  return useMutation({
    mutationFn: (profileId: string) => scanProfilesApi.export(toolName, profileId),
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useSetScanProfileEnabled(toolName: string) {
  const invalidate = useInvalidateProfiles(toolName);
  return useMutation({
    mutationFn: ({ profileId, enabled }: { profileId: string; enabled: boolean }) =>
      enabled ? scanProfilesApi.enable(toolName, profileId) : scanProfilesApi.disable(toolName, profileId),
    onSuccess: (_result, variables) => {
      invalidate();
      toast.success(variables.enabled ? "Profile enabled." : "Profile disabled.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
