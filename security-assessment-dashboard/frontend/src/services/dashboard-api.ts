import { apiGet } from "@/services/api-client";
import type { Dashboard, Statistics } from "@/types/dashboard";

export const dashboardApi = {
  get: (assessmentId?: string) => apiGet<Dashboard>("/dashboard", assessmentId ? { assessment_id: assessmentId } : undefined),
  statistics: (assessmentId?: string) => apiGet<Statistics>("/statistics", assessmentId ? { assessment_id: assessmentId } : undefined),
};
