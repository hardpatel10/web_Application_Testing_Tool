import { Filter, Layers, Search as SearchIcon, SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { EmptyState } from "@/components/common/EmptyState";
import { Input } from "@/components/ui/input";
import { PaginationControls } from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useTechnologies } from "@/hooks/useHostInventory";
import { TECHNOLOGY_CATEGORY_OPTIONS, type TechnologyCategory } from "@/types/host-inventory";

const PAGE_SIZE = 25;

export default function Technologies() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<TechnologyCategory | "all">("all");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useTechnologies({
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
        <h1 className="text-4xl font-semibold tracking-normal text-foreground">Technologies</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">Software/product signatures extracted from every service.</p>
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/70 p-3 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[240px] flex-1">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Search by name..." className="pl-9" />
          </div>
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            <SlidersHorizontal className="h-4 w-4" /> Filters
          </div>
          <Select value={category} onValueChange={(v) => { setCategory(v as TechnologyCategory | "all"); setPage(1); }}>
            <SelectTrigger className="w-48"><SelectValue placeholder="Category" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All categories</SelectItem>
              {TECHNOLOGY_CATEGORY_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {isLoading && <div className="space-y-3 rounded-2xl border border-border/70 bg-card/60 p-4"><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /></div>}
      {isError && <EmptyState title="Couldn't load technologies" description="Something went wrong talking to the backend." icon={<Filter className="h-5 w-5" />} />}
      {!isLoading && !isError && data && data.items.length === 0 && (
        <EmptyState title="No technologies extracted" description="Run a service/version detection scan to populate this." icon={<Layers className="h-5 w-5" />} />
      )}
      {!isLoading && !isError && data && data.items.length > 0 && (
        <div className="space-y-4 rounded-2xl border border-border/70 bg-card/70 p-4 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Vendor</TableHead>
                <TableHead>Version</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Last Seen</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((technology) => (
                <TableRow key={technology.id} className="cursor-pointer" onClick={() => navigate(`/hosts/${technology.host_id}`)}>
                  <TableCell className="font-medium text-foreground">{technology.name}</TableCell>
                  <TableCell>{technology.vendor ?? "—"}</TableCell>
                  <TableCell>{technology.version ?? "—"}</TableCell>
                  <TableCell className="capitalize text-muted-foreground">{technology.category.replace("_", " ")}</TableCell>
                  <TableCell className="text-muted-foreground">{new Date(technology.last_seen).toLocaleString()}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <PaginationControls page={data.page} totalPages={data.total_pages} total={data.total} pageSize={data.page_size} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}
