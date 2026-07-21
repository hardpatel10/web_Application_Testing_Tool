import { Filter, MonitorSmartphone, Search as SearchIcon } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { EmptyState } from "@/components/common/EmptyState";
import { Input } from "@/components/ui/input";
import { PaginationControls } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useOperatingSystems } from "@/hooks/useHostInventory";

const PAGE_SIZE = 25;

export default function OperatingSystems() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useOperatingSystems({
    search: search || undefined,
    sort_by: "accuracy",
    sort_dir: "desc",
    page,
    page_size: PAGE_SIZE,
  });

  return (
    <div className="space-y-7">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-primary/80">Inventory</p>
        <h1 className="text-4xl font-semibold tracking-normal text-foreground">Operating Systems</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          Every OS candidate match reported by a scan — not just the single best guess.
        </p>
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/70 p-3 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
        <div className="relative min-w-[240px] flex-1">
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Search by name..." className="pl-9" />
        </div>
      </div>

      {isLoading && <div className="space-y-3 rounded-2xl border border-border/70 bg-card/60 p-4"><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /></div>}
      {isError && <EmptyState title="Couldn't load operating systems" description="Something went wrong talking to the backend." icon={<Filter className="h-5 w-5" />} />}
      {!isLoading && !isError && data && data.items.length === 0 && (
        <EmptyState title="No OS candidates recorded" description="Run an OS-detection scan to populate this." icon={<MonitorSmartphone className="h-5 w-5" />} />
      )}
      {!isLoading && !isError && data && data.items.length > 0 && (
        <div className="space-y-4 rounded-2xl border border-border/70 bg-card/70 p-4 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Family</TableHead>
                <TableHead>Accuracy</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Last Seen</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((os) => (
                <TableRow key={os.id} className="cursor-pointer" onClick={() => navigate(`/hosts/${os.host_id}`)}>
                  <TableCell className="font-medium text-foreground">{os.name}</TableCell>
                  <TableCell>{os.family ?? "—"}</TableCell>
                  <TableCell>{os.accuracy}%</TableCell>
                  <TableCell className="text-muted-foreground">{os.source}</TableCell>
                  <TableCell className="text-muted-foreground">{new Date(os.last_seen).toLocaleString()}</TableCell>
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
