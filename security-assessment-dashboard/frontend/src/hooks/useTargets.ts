import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { assessmentKeys } from "@/hooks/useAssessments";
import { invalidateInventoryViews } from "@/hooks/useInvalidateInventoryViews";
import { ApiError } from "@/services/api-client";
import { targetsApi } from "@/services/targets-api";
import type { TargetCreatePayload, TargetListParams, TargetType, TargetUpdatePayload } from "@/types/target";

const targetKeys = {
  all: (assessmentId: string) => ["assessments", assessmentId, "targets"] as const,
  list: (assessmentId: string, params: TargetListParams) => [...targetKeys.all(assessmentId), "list", params] as const,
};

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong.";
}

export function useTargets(assessmentId: string, params: TargetListParams) {
  return useQuery({
    queryKey: targetKeys.list(assessmentId, params),
    queryFn: () => targetsApi.list(assessmentId, params),
    enabled: Boolean(assessmentId),
    placeholderData: (previous) => previous,
  });
}

function useInvalidateTargets(assessmentId: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: targetKeys.all(assessmentId) });
    queryClient.invalidateQueries({ queryKey: assessmentKeys.detail(assessmentId) });
    queryClient.invalidateQueries({ queryKey: assessmentKeys.history(assessmentId) });
  };
}

export function useCreateTarget(assessmentId: string) {
  const invalidate = useInvalidateTargets(assessmentId);
  return useMutation({
    mutationFn: (payload: TargetCreatePayload) => targetsApi.create(assessmentId, payload),
    onSuccess: () => {
      invalidate();
      toast.success("Target added.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useUpdateTarget(assessmentId: string) {
  const invalidate = useInvalidateTargets(assessmentId);
  return useMutation({
    mutationFn: ({ targetId, payload }: { targetId: string; payload: TargetUpdatePayload }) =>
      targetsApi.update(assessmentId, targetId, payload),
    onSuccess: () => {
      invalidate();
      toast.success("Target updated.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useDeleteTarget(assessmentId: string) {
  const queryClient = useQueryClient();
  const invalidate = useInvalidateTargets(assessmentId);
  return useMutation({
    mutationFn: (targetId: string) => targetsApi.remove(assessmentId, targetId),
    onSuccess: () => {
      invalidate();
      // A removed target hard-deletes (cascades to) its hosts/services/findings --
      // the cross-assessment aggregate views need invalidating too, not just this
      // assessment's own target list.
      invalidateInventoryViews(queryClient);
      toast.success("Target removed.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useToggleTargetEnabled(assessmentId: string) {
  const invalidate = useInvalidateTargets(assessmentId);
  return useMutation({
    mutationFn: ({ targetId, enabled }: { targetId: string; enabled: boolean }) =>
      enabled ? targetsApi.enable(assessmentId, targetId) : targetsApi.disable(assessmentId, targetId),
    onSuccess: () => invalidate(),
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useDuplicateTarget(assessmentId: string) {
  const invalidate = useInvalidateTargets(assessmentId);
  return useMutation({
    mutationFn: ({ targetId, targetValue }: { targetId: string; targetValue?: string }) =>
      targetsApi.duplicate(assessmentId, targetId, targetValue),
    onSuccess: () => {
      invalidate();
      toast.success("Target duplicated.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useValidateTarget(assessmentId: string) {
  return useMutation({
    mutationFn: ({ targetType, targetValue }: { targetType: TargetType; targetValue: string }) =>
      targetsApi.validate(assessmentId, targetType, targetValue),
  });
}

export function useBulkImportTargets(assessmentId: string) {
  const invalidate = useInvalidateTargets(assessmentId);
  return useMutation({
    mutationFn: (file: File) => targetsApi.bulkImport(assessmentId, file),
    onSuccess: (result) => {
      invalidate();
      toast.success(`Imported ${result.imported} target(s).`);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
