import { AlertTriangle, ExternalLink, RefreshCw, ShieldCheck } from "lucide-react";

import { ToolConfigurationForm } from "@/components/tools/ToolConfigurationForm";
import { ToolHealthBadge, ToolStatusBadge } from "@/components/tools/ToolStatusBadges";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCheckToolHealth, useTool, useValidateTools } from "@/hooks/useTools";

interface ToolDetailsDialogProps {
  toolName: string | null;
  onOpenChange: (open: boolean) => void;
}

export function ToolDetailsDialog({ toolName, onOpenChange }: ToolDetailsDialogProps) {
  const { data: tool, isLoading } = useTool(toolName ?? undefined);
  const healthMutation = useCheckToolHealth(toolName ?? "");
  const validateMutation = useValidateTools();

  return (
    <Dialog open={Boolean(toolName)} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        {isLoading && (
          <div className="space-y-3">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-32 w-full" />
          </div>
        )}

        {tool && (
          <>
            <DialogHeader>
              <div className="flex flex-wrap items-center gap-2">
                <DialogTitle>{tool.display_name}</DialogTitle>
                <ToolStatusBadge status={tool.status} />
                <ToolHealthBadge health={tool.health_status} />
              </div>
              <DialogDescription>
                v{tool.version ?? "unknown"} · {tool.license}
                {tool.homepage && (
                  <>
                    {" · "}
                    <a href={tool.homepage} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">
                      Homepage <ExternalLink className="h-3 w-3" />
                    </a>
                  </>
                )}
              </DialogDescription>
            </DialogHeader>

            {!tool.is_installed && (
              <div className="rounded-xl border border-destructive/40 bg-destructive/10 p-4 space-y-3">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-foreground">{tool.display_name} is not installed</p>
                    <p className="text-sm text-muted-foreground">
                      {tool.health_message ??
                        "Scans using this tool cannot start until it's installed and detected on this machine."}
                    </p>
                  </div>
                </div>

                {tool.install_instructions && Object.keys(tool.install_instructions).length > 0 && (
                  <div className="space-y-2">
                    {Object.entries(tool.install_instructions).map(([platform, instructions]) => (
                      <div key={platform} className="rounded-lg border border-border/60 bg-background/60 p-3">
                        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{platform}</p>
                        <p className="mt-1 text-sm text-foreground">{instructions}</p>
                      </div>
                    ))}
                  </div>
                )}

                <div className="flex flex-wrap items-center gap-2">
                  {tool.homepage && (
                    <a
                      href={tool.homepage}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                    >
                      Official source / downloads <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    className="ml-auto"
                    onClick={() => healthMutation.mutate()}
                    disabled={healthMutation.isPending}
                  >
                    <RefreshCw className={healthMutation.isPending ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Recheck
                    Installation
                  </Button>
                </div>
              </div>
            )}

            <Tabs defaultValue="overview">
              <TabsList>
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="configuration">Configuration</TabsTrigger>
                <TabsTrigger value="diagnostics">Diagnostics</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4">
                <p className="text-sm leading-6 text-muted-foreground">{tool.description}</p>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <InfoRow label="Executable path" value={tool.installation_path ?? "Not found"} mono />
                  <InfoRow label="Plugin ID" value={tool.name} mono />
                  <InfoRow label="Supported targets" value={tool.supported_targets.join(", ") || "None"} />
                  <InfoRow label="Supported output formats" value={tool.supported_output_formats.join(", ") || "None"} />
                  <InfoRow label="Required binaries" value={tool.required_binaries.join(", ") || "None"} />
                  <InfoRow
                    label="Dependencies"
                    value={
                      tool.dependencies.length === 0
                        ? "None"
                        : tool.missing_dependencies.length > 0
                          ? `Missing: ${tool.missing_dependencies.join(", ")}`
                          : tool.dependencies.join(", ")
                    }
                    warn={tool.missing_dependencies.length > 0}
                  />
                  <InfoRow
                    label="Last checked"
                    value={tool.last_checked_at ? new Date(tool.last_checked_at).toLocaleString() : "Never"}
                  />
                </div>
              </TabsContent>

              <TabsContent value="configuration">
                <ToolConfigurationForm tool={tool} />
              </TabsContent>

              <TabsContent value="diagnostics" className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" onClick={() => healthMutation.mutate()} disabled={healthMutation.isPending}>
                    <ShieldCheck className="h-4 w-4" /> Run Health Check
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => validateMutation.mutate(tool.name)}
                    disabled={validateMutation.isPending}
                  >
                    <RefreshCw className={validateMutation.isPending ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Validate
                  </Button>
                </div>

                <div className="rounded-xl border border-border/60 bg-secondary/25 p-4">
                  <p className="text-sm font-medium text-foreground">Health message</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {healthMutation.data?.message ?? tool.health_message ?? "No health check has been run yet."}
                  </p>
                </div>

                <ValidationPanel
                  valid={validateMutation.data?.[0]?.valid ?? tool.validation_valid}
                  errors={validateMutation.data?.[0]?.errors ?? tool.validation_errors}
                  warnings={validateMutation.data?.[0]?.warnings ?? tool.validation_warnings}
                />

                <div className="rounded-xl border border-dashed border-border/70 bg-secondary/15 p-4">
                  <p className="text-sm font-medium text-foreground">Execution logs</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    No executions have been logged — tool execution isn't implemented yet (detection and configuration
                    only, this phase).
                  </p>
                </div>
              </TabsContent>
            </Tabs>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function InfoRow({ label, value, mono, warn }: { label: string; value: string; mono?: boolean; warn?: boolean }) {
  return (
    <div className="rounded-xl border border-border/60 bg-secondary/25 p-3">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={`mt-1 text-sm ${mono ? "break-all font-mono" : ""} ${warn ? "text-destructive" : "text-foreground"}`}>{value}</p>
    </div>
  );
}

function ValidationPanel({ valid, errors, warnings }: { valid: boolean; errors: string[]; warnings: string[] }) {
  return (
    <div className="rounded-xl border border-border/60 bg-secondary/25 p-4">
      <div className="flex items-center gap-2">
        <Badge variant={valid ? "success" : "destructive"}>{valid ? "Valid" : "Invalid"}</Badge>
      </div>
      {errors.length > 0 && (
        <ul className="mt-2 list-inside list-disc text-sm text-destructive">
          {errors.map((error) => (
            <li key={error}>{error}</li>
          ))}
        </ul>
      )}
      {warnings.length > 0 && (
        <ul className="mt-2 list-inside list-disc text-sm text-amber-400">
          {warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}
      {errors.length === 0 && warnings.length === 0 && (
        <p className="mt-2 text-sm text-muted-foreground">No issues found.</p>
      )}
    </div>
  );
}
