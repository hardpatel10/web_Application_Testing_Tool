import { useQuery } from "@tanstack/react-query";

import { hostsApi, searchApi } from "@/services/host-inventory-api";
import type { HostListParams } from "@/types/host-inventory";

/**
 * Only host list/detail + search remain as standalone hooks -- per-tool inventory concepts
 * (services/technologies/observations/operating systems) are no longer standalone pages; that
 * data now only ever appears nested inside `useHost()`'s own `HostDetail` response, contextually
 * within an Assessment's "Assets Discovered" tab.
 */
export const hostInventoryKeys = {
  all: ["host-inventory"] as const,
  hosts: (params?: HostListParams) => [...hostInventoryKeys.all, "hosts", params ?? {}] as const,
  host: (id: string) => [...hostInventoryKeys.all, "host", id] as const,
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

export function useHostSearch(query: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: hostInventoryKeys.search(query),
    queryFn: () => searchApi.search(query),
    enabled: (options?.enabled ?? true) && query.trim().length > 0,
  });
}
