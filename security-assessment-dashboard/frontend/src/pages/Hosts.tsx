import { Filter, Search as SearchIcon, Server, SlidersHorizontal } from "lucide-react";
import { useState } from "react";

import { HostTable } from "@/components/hosts/HostTable";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PaginationControls } from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useHosts } from "@/hooks/useHostInventory";
import { HOST_STATE_OPTIONS, HOST_TYPE_OPTIONS, type HostState, type HostType } from "@/types/host-inventory";

const PAGE_SIZE = 20;

export default function Hosts() {
  const [search, setSearch] = useState("");
  const [hostType, setHostType] = useState<HostType | "all">("all");
  const [state, setState] = useState<HostState | "all">("all");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useHosts({
    search: search || undefined,
    host_type: hostType === "all" ? undefined : hostType,
    state: state === "all" ? undefined : state,
    sort_by: "last_seen",
    sort_dir: "desc",
    page,
    page_size: PAGE_SIZE,
  });

  const hasFilters = Boolean(search) || hostType !== "all" || state !== "all";

  function clearFilters() {
    setSearch("");
    setHostType("all");
    setState("all");
    setPage(1);
  }

  return (
    <div className="space-y-7">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-primary/80">Inventory</p>
        <h1 className="text-4xl font-semibold tracking-normal text-foreground">Discovered Hosts</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          Every host discovered by a scan, deduplicated across repeated runs — never a per-job snapshot.
        </p>
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/70 p-3 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[240px] flex-1">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
              placeholder="Search by hostname, FQDN, or IP..."
              className="pl-9"
            />
          </div>
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            <SlidersHorizontal className="h-4 w-4" />
            Filters
          </div>
          <Select value={hostType} onValueChange={(value) => { setHostType(value as HostType | "all"); setPage(1); }}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              {HOST_TYPE_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={state} onValueChange={(value) => { setState(value as HostState | "all"); setPage(1); }}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="State" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All states</SelectItem>
              {HOST_STATE_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {isLoading && (
        <div className="space-y-3 rounded-2xl border border-border/70 bg-card/60 p-4">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      )}

      {isError && (
        <EmptyState
          title="Couldn't load hosts"
          description="Something went wrong talking to the backend. Try refreshing."
          icon={<Filter className="h-5 w-5" />}
        />
      )}

      {!isLoading && !isError && data && data.items.length === 0 && (
        <EmptyState
          title={hasFilters ? "No hosts match your filters" : "No hosts discovered yet"}
          description={
            hasFilters
              ? "Try a different search, type, or state to widen the results."
              : "Run a tool (like Nmap) against an assessment's targets from the Executions page — discovered hosts will appear here."
          }
          secondaryAction={hasFilters ? <Button variant="outline" onClick={clearFilters}>Clear Filters</Button> : undefined}
          icon={<Server className="h-5 w-5" />}
        />
      )}

      {!isLoading && !isError && data && data.items.length > 0 && (
        <div className="space-y-4 rounded-2xl border border-border/70 bg-card/70 p-4 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
          <HostTable hosts={data.items} />
          <PaginationControls page={data.page} totalPages={data.total_pages} total={data.total} pageSize={data.page_size} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}
