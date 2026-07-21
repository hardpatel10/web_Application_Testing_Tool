import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/services/api-client";
import { toolsApi } from "@/services/tools-api";
import type { ToolConfigurationUpdate, ToolListParams } from "@/types/tool";

export const toolKeys = {
  all: ["tools"] as const,
  list: (params?: ToolListParams) => [...toolKeys.all, "list", params ?? {}] as const,
  detail: (name: string) => [...toolKeys.all, "detail", name] as const,
  browse: (path?: string) => [...toolKeys.all, "browse", path ?? ""] as const,
};

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong.";
}

export function useTools(params?: ToolListParams) {
  return useQuery({
    queryKey: toolKeys.list(params),
    queryFn: () => toolsApi.list(params),
  });
}

export function useTool(name: string | undefined) {
  return useQuery({
    queryKey: toolKeys.detail(name ?? ""),
    queryFn: () => toolsApi.get(name as string),
    enabled: Boolean(name),
  });
}

export function useBrowseFilesystem(path: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: toolKeys.browse(path),
    queryFn: () => toolsApi.browseFilesystem(path),
    enabled,
  });
}

export function useDiscoverTools() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => toolsApi.discover(),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: toolKeys.all });
      const installed = result.tools.filter((tool) => tool.is_installed).length;
      toast.success(`Discovery complete: ${installed} of ${result.tools.length} supported tools installed.`);
      if (result.not_loaded.length > 0) {
        toast.warning(`${result.not_loaded.length} tool plugin(s) failed to load: ${result.not_loaded.join(", ")}`);
      }
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useValidateTools() {
  return useMutation({
    mutationFn: (name?: string) => toolsApi.validate(name),
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useCheckToolHealth(name: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => toolsApi.checkHealth(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: toolKeys.all });
      toast.success(`Health check complete for ${name}.`);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export function useUpdateToolConfiguration(name: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ToolConfigurationUpdate) => toolsApi.updateConfiguration(name, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: toolKeys.all });
      toast.success(`Configuration saved for ${name}.`);
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}
