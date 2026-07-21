import { RefreshCw, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { EmptyState } from "@/components/common/EmptyState";
import { ToolCard } from "@/components/tools/ToolCard";
import { ToolsEmptyState } from "@/components/tools/ToolsEmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useDiscoverTools, useTools } from "@/hooks/useTools";
import { TOOL_HEALTH_OPTIONS, TOOL_STATUS_OPTIONS, type ToolHealthStatus, type ToolStatus } from "@/types/tool";

export default function Tools() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<ToolStatus | "all">("all");
  const [health, setHealth] = useState<ToolHealthStatus | "all">("all");
  const [sortBy, setSortBy] = useState("name");

  const { data: tools, isLoading, isError } = useTools({
    search: search || undefined,
    status: status === "all" ? undefined : status,
    health: health === "all" ? undefined : health,
    sort_by: sortBy,
  });
  const discover = useDiscoverTools();

  const hasFilters = Boolean(search) || status !== "all" || health !== "all";

  // "Nothing is installed anywhere" (the onboarding empty state) is only
  // meaningful against the *unfiltered* result — a filtered view legitimately
  // returning zero/all-missing rows (e.g. status=missing) doesn't mean that.
  const showInstallGuidance = useMemo(
    () => !hasFilters && (!tools || tools.length === 0 || tools.every((tool) => !tool.is_installed)),
    [hasFilters, tools],
  );
  const showNoMatches = hasFilters && tools && tools.length === 0;

  return (
    <div className="space-y-7">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-primary/80">Tooling</p>
          <h1 className="text-4xl font-semibold tracking-normal text-foreground">Tool Management</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Discovers, validates, and configures the security tools installed on this machine. No tool is executed
            from this page.
          </p>
        </div>
        <Button variant="outline" onClick={() => discover.mutate()} disabled={discover.isPending}>
          <RefreshCw className={discover.isPending ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
          Refresh Detection
        </Button>
      </div>

      {!isLoading && !isError && !showInstallGuidance && (
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[220px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by name or plugin id…" className="pl-9" />
          </div>
          <Select value={status} onValueChange={(value) => setStatus(value as ToolStatus | "all")}>
            <SelectTrigger className="w-44">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              {TOOL_STATUS_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={health} onValueChange={(value) => setHealth(value as ToolHealthStatus | "all")}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Health" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All health</SelectItem>
              {TOOL_HEALTH_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-44">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="name">Name</SelectItem>
              <SelectItem value="status">Status</SelectItem>
              <SelectItem value="version">Version</SelectItem>
              <SelectItem value="last_checked_at">Last Checked</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {isError && <EmptyState title="Couldn't load tools" description="Something went wrong talking to the backend. Try refreshing." />}

      {!isLoading && !isError && showInstallGuidance && (
        <ToolsEmptyState onRefresh={() => discover.mutate()} isRefreshing={discover.isPending} />
      )}

      {!isLoading && !isError && showNoMatches && (
        <EmptyState title="No tools match your filters" description="Try a different search or clear your filters." />
      )}

      {!isLoading && !isError && !showInstallGuidance && tools && tools.length > 0 && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {tools.map((tool) => (
            <ToolCard key={tool.id} tool={tool} onOpenDetails={(name) => navigate(`/tools/${name}`)} />
          ))}
        </div>
      )}
    </div>
  );
}
