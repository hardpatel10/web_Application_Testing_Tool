import { Filter, Network, Search as SearchIcon, SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { EmptyState } from "@/components/common/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { PaginationControls } from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useServices } from "@/hooks/useHostInventory";
import type { NetworkProtocol } from "@/types/host-inventory";

const PAGE_SIZE = 25;

function stateVariant(state: string): "success" | "destructive" | "secondary" {
  if (state === "open") return "success";
  if (state === "closed") return "destructive";
  return "secondary";
}

export default function Services() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [protocol, setProtocol] = useState<NetworkProtocol | "all">("all");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useServices({
    search: search || undefined,
    protocol: protocol === "all" ? undefined : protocol,
    sort_by: "last_seen",
    sort_dir: "desc",
    page,
    page_size: PAGE_SIZE,
  });

  return (
    <div className="space-y-7">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-primary/80">Inventory</p>
        <h1 className="text-4xl font-semibold tracking-normal text-foreground">Services</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">Every port/protocol observed across every host.</p>
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/70 p-3 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[240px] flex-1">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Search by service or product..." className="pl-9" />
          </div>
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            <SlidersHorizontal className="h-4 w-4" /> Filters
          </div>
          <Select value={protocol} onValueChange={(v) => { setProtocol(v as NetworkProtocol | "all"); setPage(1); }}>
            <SelectTrigger className="w-32"><SelectValue placeholder="Protocol" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All protocols</SelectItem>
              <SelectItem value="tcp">TCP</SelectItem>
              <SelectItem value="udp">UDP</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {isLoading && <div className="space-y-3 rounded-2xl border border-border/70 bg-card/60 p-4"><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /></div>}
      {isError && <EmptyState title="Couldn't load services" description="Something went wrong talking to the backend." icon={<Filter className="h-5 w-5" />} />}
      {!isLoading && !isError && data && data.items.length === 0 && (
        <EmptyState title="No services found" description="Run a scan against an assessment's targets to populate this." icon={<Network className="h-5 w-5" />} />
      )}
      {!isLoading && !isError && data && data.items.length > 0 && (
        <div className="space-y-4 rounded-2xl border border-border/70 bg-card/70 p-4 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Port</TableHead>
                <TableHead>Protocol</TableHead>
                <TableHead>State</TableHead>
                <TableHead>Service</TableHead>
                <TableHead>Product</TableHead>
                <TableHead>Vendor</TableHead>
                <TableHead>Version</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((service) => (
                <TableRow key={service.id} className="cursor-pointer" onClick={() => navigate(`/hosts/${service.host_id}`)}>
                  <TableCell className="font-mono">{service.port}</TableCell>
                  <TableCell className="uppercase text-muted-foreground">{service.protocol}</TableCell>
                  <TableCell><Badge variant={stateVariant(service.state)}>{service.state}</Badge></TableCell>
                  <TableCell>{service.service_name ?? "—"}</TableCell>
                  <TableCell>{service.product ?? "—"}</TableCell>
                  <TableCell>{service.vendor ?? "—"}</TableCell>
                  <TableCell>{service.version ?? "—"}</TableCell>
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
