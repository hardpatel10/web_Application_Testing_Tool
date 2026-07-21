import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useJobResults } from "@/hooks/useExecutions";

interface JobResultsViewProps {
  jobId: string;
  enabled: boolean;
}

export function JobResultsView({ jobId, enabled }: JobResultsViewProps) {
  const { data, isLoading } = useJobResults(jobId, { enabled });

  if (!enabled) {
    return <p className="text-sm text-muted-foreground">Results are available once the job completes.</p>;
  }

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  const hosts = data?.hosts ?? [];
  const observations = data?.observations ?? [];

  if (hosts.length === 0 && observations.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No structured results for this job — either the tool doesn't produce normalized results, or the scan found nothing.
      </p>
    );
  }

  return (
    <div className="space-y-5">
      {hosts.map((host) => (
        <div key={host.id} className="rounded-xl border border-border/60 bg-secondary/15 p-4">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <p className="font-mono text-sm font-medium text-foreground">{host.ip_address ?? host.hostname ?? host.id}</p>
            {host.hostname && host.ip_address && <span className="text-sm text-muted-foreground">({host.hostname})</span>}
            <Badge variant={host.state === "up" ? "success" : "secondary"}>{host.state}</Badge>
            {host.os_name && (
              <Badge variant="outline">
                {host.os_name}
                {host.os_accuracy != null ? ` (${host.os_accuracy}%)` : ""}
              </Badge>
            )}
          </div>

          {host.services.length === 0 ? (
            <p className="text-sm text-muted-foreground">No open ports/services found on this host.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Port</TableHead>
                  <TableHead>Protocol</TableHead>
                  <TableHead>State</TableHead>
                  <TableHead>Service</TableHead>
                  <TableHead>Product / Version</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {host.services.map((service) => (
                  <TableRow key={service.id}>
                    <TableCell className="font-mono">{service.port}</TableCell>
                    <TableCell className="uppercase text-muted-foreground">{service.protocol}</TableCell>
                    <TableCell>
                      <Badge variant={service.state === "open" ? "success" : "secondary"}>{service.state}</Badge>
                    </TableCell>
                    <TableCell>{service.service_name ?? "—"}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {[service.product, service.version].filter(Boolean).join(" ") || "—"}
                      {service.extra_info && <span className="block text-xs">{service.extra_info}</span>}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      ))}

      {observations.length > 0 && (
        <div className="rounded-xl border border-border/60 bg-secondary/15 p-4">
          <p className="mb-3 text-sm font-medium text-foreground">Observations</p>
          <div className="space-y-2">
            {observations.map((observation) => (
              <div key={observation.id} className="rounded-lg border border-border/50 bg-secondary/25 p-3 text-sm">
                <p className="font-medium text-foreground">
                  {observation.title}
                  {observation.port != null && <span className="ml-2 font-mono text-xs text-muted-foreground">port {observation.port}</span>}
                </p>
                {observation.detail && <p className="mt-1 text-muted-foreground">{observation.detail}</p>}
                <p className="mt-1 text-xs uppercase tracking-wide text-muted-foreground">{observation.source}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
