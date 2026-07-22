export interface ScanProfile {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  supported_targets: string[];
  arguments: string[];
  minimum_tool_version: string | null;
  risk_level: "low" | "medium" | "high";
  estimated_duration: string;
  built_in: boolean;
  enabled: boolean;
  // Nmap-specific
  required_ports: string | null;
  required_scripts: string[];
  script_args: Record<string, string>;
  // Nikto-specific
  tuning: string | null;
  plugins: string[];
  timeout_seconds: number | null;
  // Nuclei-specific
  templates: string[];
  tags: string[];
  exclude_tags: string[];
  severities: string[];
  // SSLScan-specific
  connect_timeout_seconds: number | null;
}

export interface ScanProfileListParams {
  query?: string;
  category?: string;
  risk_level?: string;
}

export interface ScanProfileWrite {
  id: string;
  name: string;
  description: string;
  category: string;
  icon?: string;
  supported_targets: string[];
  arguments?: string[];
  minimum_tool_version?: string | null;
  risk_level?: "low" | "medium" | "high";
  estimated_duration?: string;
  required_ports?: string | null;
  required_scripts?: string[];
  script_args?: Record<string, string>;
  tuning?: string | null;
  plugins?: string[];
  timeout_seconds?: number | null;
  templates?: string[];
  tags?: string[];
  exclude_tags?: string[];
  severities?: string[];
  connect_timeout_seconds?: number | null;
}

export interface ScanProfileDuplicateRequest {
  new_id: string;
  new_name?: string | null;
}

export interface ScanProfileImportRequest {
  profile: Record<string, unknown>;
}

export interface CommandPreviewRequest {
  profile_id: string;
  target_value: string;
  advanced_options?: Record<string, unknown> | null;
}

export interface CommandPreviewResponse {
  command: string[];
}
