import { apiGet } from "@/services/api-client";
import type { HostDetail, HostListParams, HostSummary, SearchResponse } from "@/types/host-inventory";
import type { PageResponse } from "@/types/pagination";

export const hostsApi = {
  list: (params?: HostListParams) => apiGet<PageResponse<HostSummary>>("/hosts", params as Record<string, unknown>),
  get: (id: string) => apiGet<HostDetail>(`/hosts/${id}`),
};

export const searchApi = {
  search: (query: string) => apiGet<SearchResponse>("/search", { q: query }),
};
