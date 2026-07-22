import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { jobKeys } from "@/hooks/useExecutions";
import { ApiError } from "@/services/api-client";
import { pipelineApi } from "@/services/pipeline-api";
import type { PipelineStartRequestPayload } from "@/types/pipeline";

export const pipelineKeys = {
  all: ["pipeline"] as const,
  detail: (assessmentId: string) => [...pipelineKeys.all, assessmentId] as const,
};

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong.";
}

// Same plain-polling convention as useExecutions.ts's jobKeys hooks -- one app-wide
// transport choice, not something each new live view should re-decide.
const POLL_INTERVAL_MS = 1500;

export function usePipeline(assessmentId: string | undefined, options?: { poll?: boolean }) {
  return useQuery({
    queryKey: pipelineKeys.detail(assessmentId ?? ""),
    queryFn: async () => {
      try {
        return await pipelineApi.get(assessmentId as string);
      } catch (error) {
        // No run yet is a normal, expected state for a fresh assessment -- not an error to surface.
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },
    enabled: Boolean(assessmentId),
    refetchInterval: options?.poll ? POLL_INTERVAL_MS : false,
  });
}

export function useStartPipeline(assessmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: PipelineStartRequestPayload) => pipelineApi.start(assessmentId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelineKeys.detail(assessmentId) });
      queryClient.invalidateQueries({ queryKey: jobKeys.all });
      toast.success("Assessment started -- recon is running.");
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
