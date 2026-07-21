export type HostType = "host" | "website" | "api" | "domain" | "ip";
export type HostState = "up" | "down" | "unknown";
export type NetworkProtocol = "tcp" | "udp";
export type PortState = "open" | "closed" | "filtered" | "open|filtered" | "closed|filtered" | "unfiltered";
export type TechnologyCategory = "web_server" | "database" | "language" | "framework" | "middleware" | "operating_system" | "other";
export type ObservationCategory = "network" | "web" | "tls" | "auth" | "configuration" | "os" | "other";

export const HOST_TYPE_OPTIONS: { value: HostType; label: string }[] = [
  { value: "host", label: "Host" },
  { value: "website", label: "Website" },
  { value: "api", label: "API" },
  { value: "domain", label: "Domain" },
  { value: "ip", label: "IP" },
];

export const HOST_STATE_OPTIONS: { value: HostState; label: string }[] = [
  { value: "up", label: "Up" },
  { value: "down", label: "Down" },
  { value: "unknown", label: "Unknown" },
];

export const TECHNOLOGY_CATEGORY_OPTIONS: { value: TechnologyCategory; label: string }[] = [
  { value: "web_server", label: "Web Server" },
  { value: "database", label: "Database" },
  { value: "language", label: "Language" },
  { value: "framework", label: "Framework" },
  { value: "middleware", label: "Middleware" },
  { value: "operating_system", label: "Operating System" },
  { value: "other", label: "Other" },
];

export const OBSERVATION_CATEGORY_OPTIONS: { value: ObservationCategory; label: string }[] = [
  { value: "network", label: "Network" },
  { value: "web", label: "Web" },
  { value: "tls", label: "TLS" },
  { value: "auth", label: "Auth" },
  { value: "configuration", label: "Configuration" },
  { value: "os", label: "OS" },
  { value: "other", label: "Other" },
];

export interface NetworkInterface {
  id: string;
  host_id: string;
  ip_address: string;
  version: string;
  mac_address: string | null;
  network: string | null;
  interface_name: string | null;
}

export interface Technology {
  id: string;
  host_id: string;
  service_id: string | null;
  name: string;
  vendor: string | null;
  version: string | null;
  category: TechnologyCategory;
  first_seen: string;
  last_seen: string;
}

export interface OperatingSystem {
  id: string;
  host_id: string;
  vendor: string | null;
  family: string | null;
  name: string;
  version: string | null;
  accuracy: number;
  source: string;
  first_seen: string;
  last_seen: string;
}

export interface Service {
  id: string;
  host_id: string;
  port: number;
  protocol: NetworkProtocol;
  state: PortState;
  service_name: string | null;
  product: string | null;
  vendor: string | null;
  version: string | null;
  extra_info: string | null;
  banner: string | null;
  first_seen: string;
  last_seen: string;
}

export interface ObservationEvidence {
  id: string;
  observation_id: string;
  source_tool: string;
  title: string | null;
  content: string | null;
  file_path: string | null;
  created_at: string;
}

export interface Observation {
  id: string;
  host_id: string | null;
  service_id: string | null;
  port: number | null;
  plugin: string | null;
  source: string;
  category: ObservationCategory;
  observation_type: string | null;
  title: string;
  detail: string | null;
  first_seen: string;
  last_seen: string;
  evidence: ObservationEvidence[];
}

export interface ExecutionHistoryEntry {
  execution_id: string;
  tool_name: string;
  target_value: string;
  is_new: boolean;
  created_at: string;
}

export interface HostSummary {
  id: string;
  target_id: string | null;
  assessment_id: string;
  hostname: string | null;
  fqdn: string | null;
  ipv4: string | null;
  ipv6: string | null;
  mac_address: string | null;
  host_type: HostType;
  state: HostState;
  first_seen: string;
  last_seen: string;
  service_count: number;
}

export interface HostDetail {
  id: string;
  target_id: string | null;
  assessment_id: string;
  hostname: string | null;
  fqdn: string | null;
  ipv4: string | null;
  ipv6: string | null;
  mac_address: string | null;
  mac_vendor: string | null;
  host_type: HostType;
  state: HostState;
  fingerprint: string;
  first_seen: string;
  last_seen: string;
  source_execution_id: string | null;
  network_interfaces: NetworkInterface[];
  services: Service[];
  technologies: Technology[];
  operating_systems: OperatingSystem[];
  observations: Observation[];
  execution_history: ExecutionHistoryEntry[];
}

export interface HostListParams {
  assessment_id?: string;
  target_id?: string;
  host_type?: HostType;
  state?: HostState;
  search?: string;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export interface ServiceListParams {
  host_id?: string;
  protocol?: NetworkProtocol;
  state?: PortState;
  port?: number;
  search?: string;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export interface TechnologyListParams {
  host_id?: string;
  category?: TechnologyCategory;
  search?: string;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export interface ObservationListParams {
  host_id?: string;
  service_id?: string;
  category?: ObservationCategory;
  plugin?: string;
  search?: string;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export interface OperatingSystemListParams {
  host_id?: string;
  search?: string;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export interface SearchResult {
  kind: "host" | "service" | "technology" | "observation" | "finding";
  id: string;
  host_id: string | null;
  label: string;
  detail: string | null;
}

export interface SearchResponse {
  query: string;
  hosts: SearchResult[];
  services: SearchResult[];
  technologies: SearchResult[];
  observations: SearchResult[];
  findings: SearchResult[];
}
