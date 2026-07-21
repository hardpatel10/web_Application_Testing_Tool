import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { assessmentKeys } from "@/hooks/useAssessments";
import { ApiError } from "@/services/api-client";
import { executionsApi } from "@/services/executions-api";
import type { ExecuteRequestPayload, JobListParams } from "@/types/execution";

export const jobKeys = {
  all: ["jobs"] as const,
  list: (params?: JobListParams) => [...jobKeys.all, "list", params ?? {}] as const,
  detail: (id: string) => [...jobKeys.all, "detail", id] as const,
  logs: (id: string, params?: { tail?: number; search?: string }) => [...jobKeys.all, "logs", id, params ?? {}] as const,
  progress: (assessmentId: string) => [...jobKeys.all, "progress", assessmentId] as const,
  results: (id: string) => [...jobKeys.all, "results", id] as const,
  rawOutput: (id: string) => [...jobKeys.all, "raw-output", id] as const,
};

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong.";
}

// Polling (not a websocket/SSE) is the deliberate choice for "live" updates
// here -- it matches every other TanStack Query hook in this app and needs
// no new transport, consistent with the execution engine's own "everything
// runs locally, nothing distributed" scope.
const POLL_INTERVAL_MS = 1500;

export function useJobs(params?: JobListParams, options?: { poll?: boolean }) {
  return useQuery({
    queryKey: jobKeys.list(params),
    queryFn: () => executionsApi.listJobs(params),
    refetchInterval: options?.poll ? POLL_INTERVAL_MS : false,
  });
}

export function useJob(jobId: string | undefined, options?: { poll?: boolean }) {
  return useQuery({
    queryKey: jobKeys.detail(jobId ?? ""),
    queryFn: () => executionsApi.getJob(jobId as string),
    enabled: Boolean(jobId),
    refetchInterval: options?.poll ? POLL_INTERVAL_MS : false,
  });
}

export function useJobLogs(jobId: string | undefined, params?: { tail?: number; search?: string }, options?: { poll?: boolean }) {
  return useQuery({
    queryKey: jobKeys.logs(jobId ?? "", params),
    queryFn: () => executionsApi.getLogs(jobId as string, params),
    enabled: Boolean(jobId),
    refetchInterval: options?.poll ? POLL_INTERVAL_MS : false,
  });
}

export function useJobResults(jobId: string | undefined, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: jobKeys.results(jobId ?? ""),
    queryFn: () => executionsApi.getResults(jobId as string),
    enabled: Boolean(jobId) && (options?.enabled ?? true),
  });
}

export function useJobRawOutput(jobId: string | undefined) {
  return useQuery({
    queryKey: jobKeys.rawOutput(jobId ?? ""),
    queryFn: () => executionsApi.getRawOutput(jobId as string),
    enabled: false,
  });
}

export function useAssessmentProgress(assessmentId: string | undefined, options?: { poll?: boolean }) {
  return useQuery({
    queryKey: jobKeys.progress(assessmentId ?? ""),
    queryFn: () => executionsApi.progress(assessmentId as string),
    enabled: Boolean(assessmentId),
    refetchInterval: options?.poll ? POLL_INTERVAL_MS : false,
  });
}

export function useExecuteAssessment(assessmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ExecuteRequestPayload) => executionsApi.execute(assessmentId, payload),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: jobKeys.all });
      queryClient.invalidateQueries({ queryKey: assessmentKeys.detail(assessmentId) });
      const message =
        result.skipped_count > 0
          ? `Queued ${result.queued_count} job(s), skipped ${result.skipped_count}.`
          : `Queued ${result.queued_count} job(s).`;
      toast.success(message);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useCancelJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => executionsApi.cancelJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jobKeys.all });
      toast.success("Job cancelled.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useRetryJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) => executionsApi.retryJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jobKeys.all });
      toast.success("Job re-queued.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
