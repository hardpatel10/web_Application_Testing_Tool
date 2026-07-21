export interface ScanProfile {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  supported_targets: string[];
  arguments: string[];
  required_ports: string | null;
  required_scripts: string[];
  script_args: Record<string, string>;
  minimum_nmap_version: string | null;
  risk_level: "low" | "medium" | "high";
  estimated_duration: string;
  built_in: boolean;
}

export interface ScanProfileListParams {
  query?: string;
  category?: string;
  risk_level?: string;
}
