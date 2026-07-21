import type { RawOutputFormat } from "@/types/plugin";
import type { TargetType } from "@/types/target";

export type ToolStatus = "installed" | "missing" | "disabled" | "misconfigured" | "unsupported_version";
export type ToolHealthStatus = "healthy" | "warning" | "error";

export interface ToolSummary {
  id: string;
  name: string;
  display_name: string;
  version: string | null;
  status: ToolStatus;
  health_status: ToolHealthStatus | null;
  enabled: boolean;
  is_installed: boolean;
  last_checked_at: string | null;
  supported_targets: TargetType[];
  supported_output_formats: RawOutputFormat[];
}

export interface ToolConfiguration {
  timeout: number | null;
  working_directory: string | null;
  custom_executable_path: string | null;
  http_proxy: string | null;
  https_proxy: string | null;
  socks_proxy: string | null;
  rate_limit: number | null;
  retries: number | null;
  output_directory: string | null;
  temp_directory: string | null;
  arguments: string[];
  environment_variables: Record<string, string>;
  wordlists: Record<string, string>;
}

export type ToolConfigurationUpdate = Partial<ToolConfiguration> & { enabled?: boolean };

export interface ToolDetail {
  id: string;
  name: string;
  display_name: string;
  description: string;
  homepage: string | null;
  documentation_url: string | null;
  install_instructions: Record<string, string> | null;
  license: string;
  version: string | null;
  installation_path: string | null;
  status: ToolStatus;
  health_status: ToolHealthStatus | null;
  health_message: string | null;
  enabled: boolean;
  is_installed: boolean;
  last_checked_at: string | null;
  supported_platforms: string[];
  supported_targets: TargetType[];
  supported_output_formats: RawOutputFormat[];
  required_binaries: string[];
  dependencies: string[];
  missing_dependencies: string[];
  configuration: ToolConfiguration;
  validation_valid: boolean;
  validation_errors: string[];
  validation_warnings: string[];
  created_at: string;
}

export interface ToolHealthResult {
  name: string;
  status: ToolHealthStatus;
  installed: boolean;
  version_detected: string | null;
  message: string | null;
  checked_at: string;
}

export interface ToolValidationResult {
  name: string;
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface ToolDiscoveryResult {
  tools: ToolSummary[];
  not_loaded: string[];
}

export interface FilesystemEntry {
  name: string;
  path: string;
  is_directory: boolean;
}

export interface FilesystemBrowseResult {
  path: string;
  parent: string | null;
  entries: FilesystemEntry[];
}

export interface ToolListParams {
  search?: string;
  status?: ToolStatus;
  health?: ToolHealthStatus;
  sort_by?: string;
  sort_desc?: boolean;
}

export const TOOL_STATUS_OPTIONS: { value: ToolStatus; label: string }[] = [
  { value: "installed", label: "Installed" },
  { value: "missing", label: "Missing" },
  { value: "disabled", label: "Disabled" },
  { value: "misconfigured", label: "Misconfigured" },
  { value: "unsupported_version", label: "Unsupported Version" },
];

export const TOOL_HEALTH_OPTIONS: { value: ToolHealthStatus; label: string }[] = [
  { value: "healthy", label: "Healthy" },
  { value: "warning", label: "Warning" },
  { value: "error", label: "Error" },
];
