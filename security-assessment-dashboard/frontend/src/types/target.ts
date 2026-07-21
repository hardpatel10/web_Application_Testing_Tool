export type TargetType = "ipv4" | "ipv6" | "cidr" | "hostname" | "domain" | "url";

export interface Target {
  id: string;
  assessment_id: string;
  target_type: TargetType;
  target_value: string;
  resolved_ip: string | null;
  notes: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface TargetCreatePayload {
  target_type: TargetType;
  target_value: string;
  notes?: string | null;
}

export interface TargetUpdatePayload {
  target_type?: TargetType;
  target_value?: string;
  notes?: string | null;
  enabled?: boolean;
}

export interface TargetValidateResult {
  valid: boolean;
  normalized_value: string | null;
  message: string | null;
}

export interface TargetImportError {
  line_number: number;
  raw_value: string;
  reason: string;
}

export interface TargetBulkImportResult {
  total_lines: number;
  imported: number;
  skipped_duplicates: number;
  skipped_invalid: number;
  errors: TargetImportError[];
  imported_targets: Target[];
}

export const TARGET_TYPE_OPTIONS: { value: TargetType; label: string }[] = [
  { value: "ipv4", label: "IPv4" },
  { value: "ipv6", label: "IPv6" },
  { value: "cidr", label: "CIDR" },
  { value: "hostname", label: "Hostname" },
  { value: "domain", label: "Domain" },
  { value: "url", label: "URL" },
];

export interface TargetListParams {
  search?: string;
  target_type?: TargetType;
  enabled?: boolean;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}
