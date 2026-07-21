import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { HostSummary } from "@/types/host-inventory";

interface HostTableProps {
  hosts: HostSummary[];
  onSelectHost: (hostId: string) => void;
  selectedHostId?: string | null;
}

/** A pure list + selection callback -- no navigation of its own, so any context (an Assessment's
 * "Assets Discovered" tab, a future drill-down view) can decide what selecting a host means. */
export function HostTable({ hosts, onSelectHost, selectedHostId }: HostTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Host</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>State</TableHead>
          <TableHead>Services</TableHead>
          <TableHead>First Seen</TableHead>
          <TableHead>Last Seen</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {hosts.map((host) => (
          <TableRow
            key={host.id}
            className={`cursor-pointer ${selectedHostId === host.id ? "bg-secondary/40" : ""}`}
            onClick={() => onSelectHost(host.id)}
          >
            <TableCell className="font-medium text-foreground">
              <span className="font-mono">{host.ipv4 ?? host.ipv6 ?? "—"}</span>
              {host.hostname && <span className="ml-2 text-muted-foreground">({host.hostname})</span>}
            </TableCell>
            <TableCell className="capitalize text-muted-foreground">{host.host_type}</TableCell>
            <TableCell>
              <Badge variant={host.state === "up" ? "success" : host.state === "down" ? "destructive" : "secondary"}>
                {host.state}
              </Badge>
            </TableCell>
            <TableCell>{host.service_count}</TableCell>
            <TableCell className="text-muted-foreground">{new Date(host.first_seen).toLocaleString()}</TableCell>
            <TableCell className="text-muted-foreground">{new Date(host.last_seen).toLocaleString()}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
