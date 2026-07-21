import { apiGet } from "@/services/api-client";
import type {
  HostDetail,
  HostListParams,
  HostSummary,
  Observation,
  ObservationListParams,
  OperatingSystem,
  OperatingSystemListParams,
  SearchResponse,
  Service,
  ServiceListParams,
  Technology,
  TechnologyListParams,
} from "@/types/host-inventory";
import type { PageResponse } from "@/types/pagination";

export const hostsApi = {
  list: (params?: HostListParams) => apiGet<PageResponse<HostSummary>>("/hosts", params as Record<string, unknown>),
  get: (id: string) => apiGet<HostDetail>(`/hosts/${id}`),
};

export const servicesApi = {
  list: (params?: ServiceListParams) => apiGet<PageResponse<Service>>("/services", params as Record<string, unknown>),
};

export const technologiesApi = {
  list: (params?: TechnologyListParams) => apiGet<PageResponse<Technology>>("/technologies", params as Record<string, unknown>),
};

export const observationsApi = {
  list: (params?: ObservationListParams) => apiGet<PageResponse<Observation>>("/observations", params as Record<string, unknown>),
};

export const operatingSystemsApi = {
  list: (params?: OperatingSystemListParams) =>
    apiGet<PageResponse<OperatingSystem>>("/operating-systems", params as Record<string, unknown>),
};

export const searchApi = {
  search: (query: string) => apiGet<SearchResponse>("/search", { q: query }),
};
