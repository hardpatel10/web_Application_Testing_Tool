import { Eye, Filter, Search as SearchIcon, SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { EmptyState } from "@/components/common/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { PaginationControls } from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useObservations } from "@/hooks/useHostInventory";
import { OBSERVATION_CATEGORY_OPTIONS, type ObservationCategory } from "@/types/host-inventory";

const PAGE_SIZE = 20;

export default function Observations() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<ObservationCategory | "all">("all");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useObservations({
    search: search || undefined,
    category: category === "all" ? undefined : category,
    sort_by: "last_seen",
    sort_dir: "desc",
    page,
    page_size: PAGE_SIZE,
  });

  return (
    <div className="space-y-7">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-primary/80">Inventory</p>
        <h1 className="text-4xl font-semibold tracking-normal text-foreground">Observations</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          Neutral, non-vulnerability facts reported by scans — never a judged finding.
        </p>
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/70 p-3 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[240px] flex-1">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Search by title or detail..." className="pl-9" />
          </div>
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            <SlidersHorizontal className="h-4 w-4" /> Filters
          </div>
          <Select value={category} onValueChange={(v) => { setCategory(v as ObservationCategory | "all"); setPage(1); }}>
            <SelectTrigger className="w-44"><SelectValue placeholder="Category" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All categories</SelectItem>
              {OBSERVATION_CATEGORY_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {isLoading && <div className="space-y-3 rounded-2xl border border-border/70 bg-card/60 p-4"><Skeleton className="h-16 w-full" /><Skeleton className="h-16 w-full" /></div>}
      {isError && <EmptyState title="Couldn't load observations" description="Something went wrong talking to the backend." icon={<Filter className="h-5 w-5" />} />}
      {!isLoading && !isError && data && data.items.length === 0 && (
        <EmptyState title="No observations recorded" description="Scans will populate this as they run scripts/checks against your targets." icon={<Eye className="h-5 w-5" />} />
      )}
      {!isLoading && !isError && data && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((observation) => (
            <div
              key={observation.id}
              className="cursor-pointer rounded-xl border border-border/60 bg-card/70 p-4 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] transition-colors hover:border-border"
              onClick={() => observation.host_id && navigate(`/hosts/${observation.host_id}`)}
            >
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <Badge variant="outline" className="capitalize">{observation.category}</Badge>
                {observation.plugin && <span className="text-xs uppercase tracking-wide text-muted-foreground">{observation.plugin}</span>}
                <span className="font-medium text-foreground">{observation.title}</span>
                {observation.port != null && <span className="font-mono text-xs text-muted-foreground">port {observation.port}</span>}
                <span className="ml-auto text-xs text-muted-foreground">{new Date(observation.last_seen).toLocaleString()}</span>
              </div>
              {observation.detail && <p className="mt-2 line-clamp-2 whitespace-pre-wrap text-sm text-muted-foreground">{observation.detail}</p>}
            </div>
          ))}
          <PaginationControls page={data.page} totalPages={data.total_pages} total={data.total} pageSize={data.page_size} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}
