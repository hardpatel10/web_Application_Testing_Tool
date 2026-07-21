import { ArrowLeft, Server } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { EmptyState } from "@/components/common/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useHost } from "@/hooks/useHostInventory";

function stateVariant(state: string): "success" | "destructive" | "secondary" {
  if (state === "up" || state === "open") return "success";
  if (state === "down" || state === "closed") return "destructive";
  return "secondary";
}

export default function HostDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const hostId = id ?? "";

  const { data: host, isLoading, isError } = useHost(hostId);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (isError || !host) {
    return (
      <EmptyState
        title="Host not found"
        description="It may not exist, or its assessment was deleted."
        action={
          <Button variant="outline" onClick={() => navigate("/hosts")}>
            Back to hosts
          </Button>
        }
        icon={<Server className="h-5 w-5" />}
      />
    );
  }

  return (
    <div className="space-y-7">
      <div className="rounded-3xl border border-border/70 bg-card/70 p-6 shadow-[0_24px_100px_-60px_rgba(0,0,0,0.95)] backdrop-blur-xl">
        <div className="space-y-2">
          <Link to="/hosts" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" /> Back to hosts
          </Link>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-4xl font-semibold tracking-normal text-foreground font-mono">
              {host.ipv4 ?? host.ipv6 ?? host.hostname ?? host.id}
            </h1>
            <Badge variant={stateVariant(host.state)}>{host.state}</Badge>
            <Badge variant="outline" className="capitalize">{host.host_type}</Badge>
          </div>
          {host.hostname && <p className="text-sm text-muted-foreground">{host.hostname}</p>}
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList className="w-full justify-start overflow-x-auto sm:w-auto">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="interfaces">Network Interfaces ({host.network_interfaces.length})</TabsTrigger>
          <TabsTrigger value="services">Services ({host.services.length})</TabsTrigger>
          <TabsTrigger value="technologies">Technologies ({host.technologies.length})</TabsTrigger>
          <TabsTrigger value="os">Operating System ({host.operating_systems.length})</TabsTrigger>
          <TabsTrigger value="observations">Observations ({host.observations.length})</TabsTrigger>
          <TabsTrigger value="history">Execution History ({host.execution_history.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <Card>
            <CardContent className="grid grid-cols-2 gap-4 pt-6 text-sm sm:grid-cols-3 lg:grid-cols-4">
              <Field label="Hostname" value={host.hostname ?? "—"} />
              <Field label="FQDN" value={host.fqdn ?? "—"} />
              <Field label="IPv4" value={host.ipv4 ?? "—"} />
              <Field label="IPv6" value={host.ipv6 ?? "—"} />
              <Field label="MAC Address" value={host.mac_address ?? "—"} />
              <Field label="MAC Vendor" value={host.mac_vendor ?? "—"} />
              <Field label="First Seen" value={new Date(host.first_seen).toLocaleString()} />
              <Field label="Last Seen" value={new Date(host.last_seen).toLocaleString()} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="interfaces">
          {host.network_interfaces.length === 0 ? (
            <EmptyState title="No network interfaces recorded" description="This scanner didn't report a structured address list for this host." icon={<Server className="h-5 w-5" />} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>IP Address</TableHead>
                  <TableHead>Version</TableHead>
                  <TableHead>MAC Address</TableHead>
                  <TableHead>Network</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {host.network_interfaces.map((iface) => (
                  <TableRow key={iface.id}>
                    <TableCell className="font-mono">{iface.ip_address}</TableCell>
                    <TableCell className="uppercase text-muted-foreground">{iface.version}</TableCell>
                    <TableCell>{iface.mac_address ?? "—"}</TableCell>
                    <TableCell>{iface.network ?? "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TabsContent>

        <TabsContent value="services">
          {host.services.length === 0 ? (
            <EmptyState title="No services found" description="No open ports/services have been recorded for this host." icon={<Server className="h-5 w-5" />} />
          ) : (
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
                  <TableHead>Banner</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {host.services.map((service) => (
                  <TableRow key={service.id}>
                    <TableCell className="font-mono">{service.port}</TableCell>
                    <TableCell className="uppercase text-muted-foreground">{service.protocol}</TableCell>
                    <TableCell><Badge variant={stateVariant(service.state)}>{service.state}</Badge></TableCell>
                    <TableCell>{service.service_name ?? "—"}</TableCell>
                    <TableCell>{service.product ?? "—"}</TableCell>
                    <TableCell>{service.vendor ?? "—"}</TableCell>
                    <TableCell>{service.version ?? "—"}</TableCell>
                    <TableCell className="max-w-xs truncate text-muted-foreground">{service.banner ?? "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TabsContent>

        <TabsContent value="technologies">
          {host.technologies.length === 0 ? (
            <EmptyState title="No technologies extracted" description="Run a service/version detection scan (e.g. Nmap's Service Detection profile) to populate this." icon={<Server className="h-5 w-5" />} />
          ) : (
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
                {host.technologies.map((technology) => (
                  <TableRow key={technology.id}>
                    <TableCell className="font-medium text-foreground">{technology.name}</TableCell>
                    <TableCell>{technology.vendor ?? "—"}</TableCell>
                    <TableCell>{technology.version ?? "—"}</TableCell>
                    <TableCell className="capitalize text-muted-foreground">{technology.category.replace("_", " ")}</TableCell>
                    <TableCell className="text-muted-foreground">{new Date(technology.last_seen).toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TabsContent>

        <TabsContent value="os">
          {host.operating_systems.length === 0 ? (
            <EmptyState title="No OS candidates recorded" description="Run an OS-detection scan (e.g. Nmap's OS Detection profile) to populate this." icon={<Server className="h-5 w-5" />} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Family</TableHead>
                  <TableHead>Accuracy</TableHead>
                  <TableHead>Source</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {[...host.operating_systems]
                  .sort((a, b) => b.accuracy - a.accuracy)
                  .map((os) => (
                    <TableRow key={os.id}>
                      <TableCell className="font-medium text-foreground">{os.name}</TableCell>
                      <TableCell>{os.family ?? "—"}</TableCell>
                      <TableCell>{os.accuracy}%</TableCell>
                      <TableCell className="text-muted-foreground">{os.source}</TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          )}
        </TabsContent>

        <TabsContent value="observations" className="space-y-3">
          {host.observations.length === 0 ? (
            <EmptyState title="No observations recorded" description="Neutral, non-vulnerability facts (headers, certs, script output) will appear here as scans discover them." icon={<Server className="h-5 w-5" />} />
          ) : (
            host.observations.map((observation) => (
              <details key={observation.id} className="rounded-xl border border-border/60 bg-secondary/15 p-4">
                <summary className="flex cursor-pointer flex-wrap items-center gap-2 text-sm">
                  <Badge variant="outline" className="capitalize">{observation.category}</Badge>
                  {observation.plugin && <span className="text-xs uppercase tracking-wide text-muted-foreground">{observation.plugin}</span>}
                  <span className="font-medium text-foreground">{observation.title}</span>
                  {observation.port != null && <span className="font-mono text-xs text-muted-foreground">port {observation.port}</span>}
                </summary>
                {observation.detail && <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">{observation.detail}</p>}
                {observation.evidence.length > 0 && (
                  <div className="mt-3 space-y-2 border-t border-border/50 pt-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Evidence</p>
                    {observation.evidence.map((evidence) => (
                      <div key={evidence.id} className="rounded-lg border border-border/50 bg-black/20 p-2 font-mono text-xs text-foreground/80">
                        <p className="mb-1 text-muted-foreground">{evidence.source_tool} — {new Date(evidence.created_at).toLocaleString()}</p>
                        <p className="whitespace-pre-wrap">{evidence.content ?? evidence.file_path ?? "—"}</p>
                      </div>
                    ))}
                  </div>
                )}
              </details>
            ))
          )}
        </TabsContent>

        <TabsContent value="history">
          {host.execution_history.length === 0 ? (
            <EmptyState title="No execution history" description="Every scan that touches this host will be recorded here." icon={<Server className="h-5 w-5" />} />
          ) : (
            <ul className="space-y-3">
              {host.execution_history.map((entry) => (
                <li key={entry.execution_id} className="flex flex-wrap items-center gap-3 rounded-xl border border-border/50 bg-secondary/25 p-3 text-sm">
                  <span className="w-44 shrink-0 text-muted-foreground">{new Date(entry.created_at).toLocaleString()}</span>
                  <Badge variant={entry.is_new ? "success" : "outline"}>{entry.is_new ? "Discovered" : "Re-confirmed"}</Badge>
                  <span className="font-medium capitalize text-foreground">{entry.tool_name}</span>
                  <span className="font-mono text-muted-foreground">{entry.target_value}</span>
                </li>
              ))}
            </ul>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border/60 bg-secondary/30 p-4">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      <p className="mt-2 font-mono text-foreground">{value}</p>
    </div>
  );
}
