import { useQuery } from "@tanstack/react-query";

import { dashboardApi } from "@/services/dashboard-api";

export const dashboardKeys = {
  all: ["dashboard"] as const,
  overview: (assessmentId?: string) => [...dashboardKeys.all, assessmentId ?? null] as const,
  statistics: (assessmentId?: string) => [...dashboardKeys.all, "statistics", assessmentId ?? null] as const,
};

export function useDashboard(assessmentId?: string) {
  return useQuery({
    queryKey: dashboardKeys.overview(assessmentId),
    queryFn: () => dashboardApi.get(assessmentId),
  });
}

export function useStatistics(assessmentId?: string) {
  return useQuery({
    queryKey: dashboardKeys.statistics(assessmentId),
    queryFn: () => dashboardApi.statistics(assessmentId),
  });
}
