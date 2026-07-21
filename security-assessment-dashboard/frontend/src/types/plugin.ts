import type { TargetType } from "@/types/target";

export type SupportedPlatform = "linux" | "macos" | "windows";
export type RawOutputFormat = "xml" | "json" | "txt" | "html" | "csv";
export type PluginHealthStatus = "healthy" | "degraded" | "unhealthy" | "not_installed" | "unknown";

export interface PluginSummary {
  id: string;
  display_name: string;
  version: string;
  author: string;
  enabled: boolean;
  installed: boolean;
  validation_valid: boolean;
}

export interface PluginConfiguration {
  enabled: boolean;
  default_timeout_seconds: number;
  working_directory: string | null;
  arguments: string[];
  environment_variables: Record<string, string>;
  temp_directory: string | null;
}

export interface PluginDetail {
  id: string;
  display_name: string;
  version: string;
  author: string;
  description: string;
  homepage: string | null;
  license: string;
  supported_platforms: SupportedPlatform[];
  supported_targets: TargetType[];
  supported_output_formats: RawOutputFormat[];
  required_binaries: string[];
  documentation_url: string | null;
  dependencies: string[];
  missing_dependencies: string[];
  config: PluginConfiguration;
  validation_valid: boolean;
  validation_errors: string[];
  validation_warnings: string[];
  source_path: string;
  loaded_at: string;
}

export interface PluginHealth {
  plugin_id: string;
  status: PluginHealthStatus;
  installed: boolean;
  version_detected: string | null;
  message: string | null;
  checked_at: string;
}

export interface PluginValidationResult {
  plugin_id: string;
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface PluginDiscoveryFailure {
  directory: string;
  error: string;
}

export interface PluginReloadResult {
  registered_count: number;
  plugins: PluginSummary[];
  failures: PluginDiscoveryFailure[];
}
