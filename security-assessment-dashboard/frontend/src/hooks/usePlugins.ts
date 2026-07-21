import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/services/api-client";
import { pluginsApi } from "@/services/plugins-api";

export const pluginKeys = {
  all: ["plugins"] as const,
  list: () => [...pluginKeys.all, "list"] as const,
  detail: (id: string) => [...pluginKeys.all, "detail", id] as const,
  health: (id: string) => [...pluginKeys.all, "health", id] as const,
};

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong.";
}

export function usePlugins() {
  return useQuery({
    queryKey: pluginKeys.list(),
    queryFn: () => pluginsApi.list(),
  });
}

export function usePlugin(id: string | undefined) {
  return useQuery({
    queryKey: pluginKeys.detail(id ?? ""),
    queryFn: () => pluginsApi.get(id as string),
    enabled: Boolean(id),
  });
}

export function usePluginHealth(id: string | undefined) {
  return useQuery({
    queryKey: pluginKeys.health(id ?? ""),
    queryFn: () => pluginsApi.health(id as string),
    enabled: Boolean(id),
  });
}

export function useReloadPlugins() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => pluginsApi.reload(),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: pluginKeys.all });
      if (result.failures.length > 0) {
        toast.warning(`Reloaded: ${result.registered_count} registered, ${result.failures.length} failed.`);
      } else {
        toast.success(`Reloaded: ${result.registered_count} plugin(s) registered.`);
      }
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
