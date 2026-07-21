import { useQuery } from "@tanstack/react-query";

import { hostsApi, observationsApi, operatingSystemsApi, searchApi, servicesApi, technologiesApi } from "@/services/host-inventory-api";
import type {
  HostListParams,
  ObservationListParams,
  OperatingSystemListParams,
  ServiceListParams,
  TechnologyListParams,
} from "@/types/host-inventory";

export const hostInventoryKeys = {
  all: ["host-inventory"] as const,
  hosts: (params?: HostListParams) => [...hostInventoryKeys.all, "hosts", params ?? {}] as const,
  host: (id: string) => [...hostInventoryKeys.all, "host", id] as const,
  services: (params?: ServiceListParams) => [...hostInventoryKeys.all, "services", params ?? {}] as const,
  technologies: (params?: TechnologyListParams) => [...hostInventoryKeys.all, "technologies", params ?? {}] as const,
  observations: (params?: ObservationListParams) => [...hostInventoryKeys.all, "observations", params ?? {}] as const,
  operatingSystems: (params?: OperatingSystemListParams) => [...hostInventoryKeys.all, "operating-systems", params ?? {}] as const,
  search: (query: string) => [...hostInventoryKeys.all, "search", query] as const,
};

export function useHosts(params?: HostListParams) {
  return useQuery({
    queryKey: hostInventoryKeys.hosts(params),
    queryFn: () => hostsApi.list(params),
    placeholderData: (previous) => previous,
  });
}

export function useHost(id: string | undefined) {
  return useQuery({
    queryKey: hostInventoryKeys.host(id ?? ""),
    queryFn: () => hostsApi.get(id as string),
    enabled: Boolean(id),
  });
}

export function useServices(params?: ServiceListParams) {
  return useQuery({
    queryKey: hostInventoryKeys.services(params),
    queryFn: () => servicesApi.list(params),
    placeholderData: (previous) => previous,
  });
}

export function useTechnologies(params?: TechnologyListParams) {
  return useQuery({
    queryKey: hostInventoryKeys.technologies(params),
    queryFn: () => technologiesApi.list(params),
    placeholderData: (previous) => previous,
  });
}

export function useObservations(params?: ObservationListParams) {
  return useQuery({
    queryKey: hostInventoryKeys.observations(params),
    queryFn: () => observationsApi.list(params),
    placeholderData: (previous) => previous,
  });
}

export function useOperatingSystems(params?: OperatingSystemListParams) {
  return useQuery({
    queryKey: hostInventoryKeys.operatingSystems(params),
    queryFn: () => operatingSystemsApi.list(params),
    placeholderData: (previous) => previous,
  });
}

export function useHostSearch(query: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: hostInventoryKeys.search(query),
    queryFn: () => searchApi.search(query),
    enabled: (options?.enabled ?? true) && query.trim().length > 0,
  });
}
