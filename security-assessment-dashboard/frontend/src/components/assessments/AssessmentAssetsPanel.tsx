import { Search, Server } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/common/EmptyState";
import { HostDetailPanel } from "@/components/hosts/HostDetailPanel";
import { HostTable } from "@/components/hosts/HostTable";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useHosts } from "@/hooks/useHostInventory";
import { HOST_STATE_OPTIONS, HOST_TYPE_OPTIONS, type HostState, type HostType } from "@/types/host-inventory";

const PAGE_SIZE = 20;

/**
 * "Assets Discovered" -- the former standalone `/hosts` list + `/hosts/:id` details page,
 * scoped to one assessment and rendered inline instead. Selecting a host expands its full
 * drill-down (services/technologies/OS/observations/execution history) in place.
 */
export function AssessmentAssetsPanel({ assessmentId }: { assessmentId: string }) {
  const [search, setSearch] = useState("");
  const [hostType, setHostType] = useState<HostType | "all">("all");
  const [state, setState] = useState<HostState | "all">("all");
  const [selectedHostId, setSelectedHostId] = useState<string | null>(null);

  const { data, isLoading, isError } = useHosts({
    assessment_id: assessmentId,
    search: search || undefined,
    host_type: hostType === "all" ? undefined : hostType,
    state: state === "all" ? undefined : state,
    sort_by: "last_seen",
    sort_dir: "desc",
    page: 1,
    page_size: PAGE_SIZE,
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search hosts…" className="pl-9" />
        </div>
        <Select value={hostType} onValueChange={(v) => setHostType(v as HostType | "all")}>
          <SelectTrigger className="w-36"><SelectValue placeholder="Type" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            {HOST_TYPE_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={state} onValueChange={(v) => setState(v as HostState | "all")}>
          <SelectTrigger className="w-36"><SelectValue placeholder="State" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All states</SelectItem>
            {HOST_STATE_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading && <Skeleton className="h-40 w-full" />}
      {isError && <EmptyState title="Couldn't load hosts" description="Something went wrong talking to the backend." icon={<Server className="h-5 w-5" />} />}
      {!isLoading && !isError && data && data.items.length === 0 && (
        <EmptyState
          title="No hosts discovered yet"
          description="Run a tool against this assessment's targets to populate its inventory."
          icon={<Server className="h-5 w-5" />}
        />
      )}
      {!isLoading && !isError && data && data.items.length > 0 && (
        <HostTable hosts={data.items} onSelectHost={(id) => setSelectedHostId(id === selectedHostId ? null : id)} selectedHostId={selectedHostId} />
      )}

      {selectedHostId && <HostDetailPanel hostId={selectedHostId} onClose={() => setSelectedHostId(null)} />}
    </div>
  );
}
