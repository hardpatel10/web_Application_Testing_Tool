import { ArrowLeft, ShieldAlert } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { SeverityBadge } from "@/components/common/SeverityBadge";
import { EmptyState } from "@/components/common/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useFinding } from "@/hooks/useFindings";
import type { FindingConfidence } from "@/types/finding";

const CONFIDENCE_VARIANT: Record<FindingConfidence, "success" | "default" | "secondary" | "outline"> = {
  confirmed: "success",
  high: "default",
  medium: "secondary",
  low: "outline",
};

const REFERENCE_LABEL: Record<string, string> = {
  cwe: "CWE",
  owasp: "OWASP",
  capec: "CAPEC",
  cve: "CVE",
  vendor_url: "Vendor Advisory",
  documentation_url: "Documentation",
};

export default function FindingDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: finding, isLoading, isError } = useFinding(id);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (isError || !finding) {
    return (
      <EmptyState
        title="Finding not found"
        description="It may not exist, or its assessment was deleted."
        action={
          <Button variant="outline" onClick={() => navigate("/findings")}>
            Back to findings
          </Button>
        }
        icon={<ShieldAlert className="h-5 w-5" />}
      />
    );
  }

  return (
    <div className="space-y-7">
      <div className="rounded-3xl border border-border/70 bg-card/70 p-6 shadow-[0_24px_100px_-60px_rgba(0,0,0,0.95)] backdrop-blur-xl">
        <div className="space-y-3">
          <Link to="/findings" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" /> Back to findings
          </Link>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-semibold tracking-normal text-foreground">{finding.title}</h1>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={finding.severity} />
            <Badge variant={CONFIDENCE_VARIANT[finding.confidence]} className="capitalize">{finding.confidence} confidence</Badge>
            <Badge variant="outline" className="capitalize">{finding.status.replace("_", " ")}</Badge>
            {finding.category && <Badge variant="secondary" className="capitalize">{finding.category}</Badge>}
            <span className="font-mono text-xs text-muted-foreground">{finding.rule_id}</span>
            {finding.plugin && <span className="text-xs uppercase tracking-wide text-muted-foreground">via {finding.plugin}</span>}
          </div>
          <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
            <span>First seen {new Date(finding.first_seen).toLocaleString()}</span>
            <span>Last seen {new Date(finding.last_seen).toLocaleString()}</span>
            {finding.host && (
              <Link to={`/hosts/${finding.host.id}`} className="text-primary hover:underline">
                {finding.host.hostname ?? finding.host.ipv4 ?? finding.host.ipv6}
              </Link>
            )}
          </div>
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList className="w-full justify-start overflow-x-auto sm:w-auto">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="evidence">Evidence ({finding.evidence.length})</TabsTrigger>
          <TabsTrigger value="observations">Observations ({finding.supporting_observations.length})</TabsTrigger>
          <TabsTrigger value="services">Affected Services ({finding.affected_services.length})</TabsTrigger>
          <TabsTrigger value="references">References ({finding.references.length})</TabsTrigger>
          <TabsTrigger value="history">Execution History ({finding.execution_history.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <Card>
            <CardContent className="space-y-5 pt-6 text-sm">
              <Field label="Description" value={finding.description ?? "—"} block />
              <Field label="Impact" value={finding.impact ?? "—"} block />
              <Field label="Recommendation / Remediation" value={finding.remediation ?? "—"} block />
              <Field
                label="CVSS Score"
                value={finding.cvss_score != null ? String(finding.cvss_score) : "Not scored — see References for CWE/OWASP classification"}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="evidence">
          <div className="space-y-3">
            {finding.evidence.length === 0 && <EmptyPane text="No evidence recorded." />}
            {finding.evidence.map((item) => (
              <Card key={item.id}>
                <CardContent className="space-y-2 pt-6">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="outline">{item.source_tool}</Badge>
                    {item.title && <span className="text-sm font-medium text-foreground">{item.title}</span>}
                    <span className="ml-auto text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString()}</span>
                  </div>
                  {item.content && <p className="whitespace-pre-wrap font-mono text-xs leading-6 text-muted-foreground">{item.content}</p>}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="observations">
          <div className="space-y-3">
            {finding.supporting_observations.length === 0 && <EmptyPane text="No supporting observations linked to this finding." />}
            {finding.supporting_observations.map((observation) => (
              <Card key={observation.id}>
                <CardContent className="space-y-1 pt-6">
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <Badge variant="outline" className="capitalize">{observation.category}</Badge>
                    <span className="font-medium text-foreground">{observation.title}</span>
                    <span className="ml-auto text-xs text-muted-foreground">{new Date(observation.last_seen).toLocaleString()}</span>
                  </div>
                  {observation.detail && <p className="whitespace-pre-wrap text-sm text-muted-foreground">{observation.detail}</p>}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="services">
          <Card>
            <CardContent className="pt-6">
              {finding.affected_services.length === 0 ? (
                <EmptyPane text="No services associated with this finding's host." />
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
                    {finding.affected_services.map((service) => (
                      <TableRow key={service.id}>
                        <TableCell className="font-mono">{service.port}</TableCell>
                        <TableCell className="uppercase">{service.protocol}</TableCell>
                        <TableCell className="capitalize">{service.state}</TableCell>
                        <TableCell>{service.service_name ?? "—"}</TableCell>
                        <TableCell>{[service.product, service.version].filter(Boolean).join(" ") || "—"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="references">
          <div className="flex flex-wrap gap-2">
            {finding.references.length === 0 && <EmptyPane text="No references attached to this finding." />}
            {finding.references.map((reference) => (
              <Badge key={reference.id} variant="outline" className="text-sm">
                {REFERENCE_LABEL[reference.reference_type] ?? reference.reference_type}: {reference.reference_value}
              </Badge>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardContent className="pt-6">
              {finding.execution_history.length === 0 ? (
                <EmptyPane text="No execution history recorded for this finding's host." />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Tool</TableHead>
                      <TableHead>Target</TableHead>
                      <TableHead>Event</TableHead>
                      <TableHead>When</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {finding.execution_history.map((entry) => (
                      <TableRow key={entry.execution_id}>
                        <TableCell className="capitalize">{entry.tool_name}</TableCell>
                        <TableCell className="font-mono text-xs">{entry.target_value}</TableCell>
                        <TableCell>{entry.is_new ? "Discovered" : "Re-confirmed"}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{new Date(entry.created_at).toLocaleString()}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Field({ label, value, block }: { label: string; value: string; block?: boolean }) {
  return (
    <div className={block ? "space-y-1" : undefined}>
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={block ? "whitespace-pre-wrap text-sm leading-6 text-foreground" : "font-medium text-foreground"}>{value}</p>
    </div>
  );
}

function EmptyPane({ text }: { text: string }) {
  return <p className="rounded-xl border border-dashed border-border/60 bg-secondary/20 px-4 py-8 text-center text-sm text-muted-foreground">{text}</p>;
}
