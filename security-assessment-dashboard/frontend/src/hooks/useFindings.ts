import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { correlationApi, findingsApi } from "@/services/findings-api";
import type { FindingListParams } from "@/types/finding";

export const findingKeys = {
  all: ["findings"] as const,
  list: (params?: FindingListParams) => [...findingKeys.all, "list", params ?? {}] as const,
  detail: (id: string) => [...findingKeys.all, "detail", id] as const,
  correlationStatus: ["correlation-status"] as const,
};

export function useFindings(params?: FindingListParams) {
  return useQuery({
    queryKey: findingKeys.list(params),
    queryFn: () => findingsApi.list(params),
    placeholderData: (previous) => previous,
  });
}

export function useFinding(id: string | undefined) {
  return useQuery({
    queryKey: findingKeys.detail(id ?? ""),
    queryFn: () => findingsApi.get(id as string),
    enabled: Boolean(id),
  });
}

export function useCorrelationStatus() {
  return useQuery({
    queryKey: findingKeys.correlationStatus,
    queryFn: () => correlationApi.status(),
  });
}

export function useRunCorrelation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (assessmentId?: string) => correlationApi.run(assessmentId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: findingKeys.all });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["statistics"] });
      toast.success(
        result.findings_created > 0
          ? `Correlation complete: ${result.findings_created} new finding(s), ${result.findings_updated} re-confirmed.`
          : `Correlation complete: no new findings (${result.findings_updated} re-confirmed).`,
      );
    },
    onError: (error: Error) => toast.error(error.message || "Correlation run failed."),
  });
}
