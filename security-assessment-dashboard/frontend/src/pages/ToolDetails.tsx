import { AlertTriangle, ArrowLeft, ExternalLink, RefreshCw, Wrench } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { EmptyState } from "@/components/common/EmptyState";
import { ToolConfigurationForm } from "@/components/tools/ToolConfigurationForm";
import { ToolDiagnosticsPanel } from "@/components/tools/ToolDiagnosticsPanel";
import { ToolOverallStatusBadge } from "@/components/tools/ToolOverallStatusBadge";
import { ToolProfilesPanel } from "@/components/tools/ToolProfilesPanel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCheckToolHealth, useRefreshTool, useTool } from "@/hooks/useTools";

export default function ToolDetails() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const { data: tool, isLoading, isError } = useTool(name);
  const healthMutation = useCheckToolHealth(name ?? "");
  const refreshMutation = useRefreshTool(name ?? "");

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (isError || !tool) {
    return (
      <EmptyState
        title="Tool not found"
        description="Run discovery from the Tool Management page, or check the tool's name."
        action={
          <Button variant="outline" onClick={() => navigate("/tools")}>
            Back to Tool Management
          </Button>
        }
        icon={<Wrench className="h-5 w-5" />}
      />
    );
  }

  return (
    <div className="space-y-7">
      <div className="rounded-3xl border border-border/70 bg-card/70 p-6 shadow-[0_24px_100px_-60px_rgba(0,0,0,0.95)] backdrop-blur-xl">
        <div className="space-y-3">
          <Link to="/tools" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" /> Back to Tool Management
          </Link>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-3xl font-semibold tracking-normal text-foreground">{tool.display_name}</h1>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => refreshMutation.mutate()} disabled={refreshMutation.isPending}>
                <RefreshCw className={refreshMutation.isPending ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Refresh
              </Button>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ToolOverallStatusBadge status={tool.overall_status} />
            <span className="font-mono text-xs text-muted-foreground">{tool.name}</span>
            <span className="text-xs text-muted-foreground">
              v{tool.version ?? "unknown"}
              {tool.minimum_tool_version && ` · min v${tool.minimum_tool_version}`}
            </span>
            <span className="text-xs text-muted-foreground">{tool.license}</span>
            {tool.homepage && (
              <a
                href={tool.homepage}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
              >
                Homepage <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
          <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
            <span>Last checked {tool.last_checked_at ? new Date(tool.last_checked_at).toLocaleString() : "Never"}</span>
            <span>Last validated {tool.last_validated_at ? new Date(tool.last_validated_at).toLocaleString() : "Never"}</span>
            <span>Detected via {tool.detection_method.replace("_", " ")}</span>
          </div>
        </div>
      </div>

      {!tool.is_installed && (
        <div className="rounded-3xl border border-destructive/40 bg-destructive/10 p-5 space-y-3">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
            <div className="space-y-1">
              <p className="text-sm font-medium text-foreground">{tool.display_name} is not installed</p>
              <p className="text-sm text-muted-foreground">
                {tool.health_message ?? "Scans using this tool cannot start until it's installed and detected on this machine."}
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
          <Button variant="outline" size="sm" onClick={() => healthMutation.mutate()} disabled={healthMutation.isPending}>
            <RefreshCw className={healthMutation.isPending ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Recheck Installation
          </Button>
        </div>
      )}

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="diagnostics">Diagnostics</TabsTrigger>
          <TabsTrigger value="profiles">Profiles</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <p className="text-sm leading-6 text-muted-foreground">{tool.description}</p>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <InfoRow label="Plugin ID" value={tool.name} mono />
            <InfoRow label="Detected tool version" value={tool.version ?? "Unknown"} />
            <InfoRow label="Executable path" value={tool.installation_path ?? "Not found"} mono />
            <InfoRow label="Detection method" value={tool.detection_method.replace("_", " ")} />
            <InfoRow label="Supported targets" value={tool.supported_targets.join(", ") || "None"} />
            <InfoRow label="Supported output formats" value={tool.supported_output_formats.join(", ") || "None"} />
            <InfoRow label="Scan Profiles" value={tool.supports_profiles ? "Supported" : "Not supported"} />
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
            <InfoRow label="Last validation" value={tool.last_validated_at ? new Date(tool.last_validated_at).toLocaleString() : "Never"} />
          </div>

          {!tool.validation_valid && (
            <div className="rounded-xl border border-border/60 bg-secondary/25 p-4">
              <div className="flex items-center gap-2">
                <Badge variant="destructive">Validation issues</Badge>
              </div>
              <ul className="mt-2 list-inside list-disc text-sm text-destructive">
                {tool.validation_errors.map((error) => (
                  <li key={error}>{error}</li>
                ))}
              </ul>
              {tool.validation_warnings.length > 0 && (
                <ul className="mt-2 list-inside list-disc text-sm text-amber-400">
                  {tool.validation_warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </TabsContent>

        <TabsContent value="diagnostics">
          <ToolDiagnosticsPanel tool={tool} />
        </TabsContent>

        <TabsContent value="profiles">
          <ToolProfilesPanel tool={tool} />
        </TabsContent>

        <TabsContent value="settings">
          <ToolConfigurationForm tool={tool} />
        </TabsContent>
      </Tabs>
    </div>
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
