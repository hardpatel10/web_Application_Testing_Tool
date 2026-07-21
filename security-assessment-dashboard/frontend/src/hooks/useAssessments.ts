import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { invalidateInventoryViews } from "@/hooks/useInvalidateInventoryViews";
import { ApiError } from "@/services/api-client";
import { assessmentsApi } from "@/services/assessments-api";
import type { AssessmentCreatePayload, AssessmentListParams, AssessmentUpdatePayload } from "@/types/assessment";

export const assessmentKeys = {
  all: ["assessments"] as const,
  list: (params: AssessmentListParams) => [...assessmentKeys.all, "list", params] as const,
  detail: (id: string) => [...assessmentKeys.all, "detail", id] as const,
  history: (id: string) => [...assessmentKeys.all, "history", id] as const,
};

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong.";
}

export function useAssessments(params: AssessmentListParams) {
  return useQuery({
    queryKey: assessmentKeys.list(params),
    queryFn: () => assessmentsApi.list(params),
    placeholderData: (previous) => previous,
  });
}

export function useAssessment(id: string | undefined) {
  return useQuery({
    queryKey: assessmentKeys.detail(id ?? ""),
    queryFn: () => assessmentsApi.get(id as string),
    enabled: Boolean(id),
  });
}

export function useAssessmentHistory(id: string | undefined, page = 1) {
  return useQuery({
    queryKey: [...assessmentKeys.history(id ?? ""), page],
    queryFn: () => assessmentsApi.history(id as string, page),
    enabled: Boolean(id),
  });
}

export function useCreateAssessment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AssessmentCreatePayload) => assessmentsApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assessmentKeys.all });
      toast.success("Assessment created.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useUpdateAssessment(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AssessmentUpdatePayload) => assessmentsApi.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assessmentKeys.all });
      toast.success("Assessment updated.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useDeleteAssessment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => assessmentsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assessmentKeys.all });
      invalidateInventoryViews(queryClient);
      toast.success("Assessment deleted.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useArchiveAssessment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => assessmentsApi.archive(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assessmentKeys.all });
      toast.success("Assessment archived.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useRestoreAssessment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => assessmentsApi.restore(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assessmentKeys.all });
      toast.success("Assessment restored.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useDuplicateAssessment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: string; name?: string }) => assessmentsApi.duplicate(id, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: assessmentKeys.all });
      toast.success("Assessment duplicated.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
