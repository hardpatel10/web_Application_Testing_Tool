import { RefreshCw, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useCheckToolHealth, useToolDiagnostics, useValidateOneTool } from "@/hooks/useTools";
import type { ToolDetail } from "@/types/tool";

const DETECTION_METHOD_LABEL: Record<string, string> = {
  path: "Found on PATH",
  custom_path: "Configured custom executable path",
  search_directory: "Found in a common install directory",
  not_found: "Not found",
};

export function ToolDiagnosticsPanel({ tool }: { tool: ToolDetail }) {
  const { data: diagnostics, isLoading, refetch, isFetching } = useToolDiagnostics(tool.name);
  const healthMutation = useCheckToolHealth(tool.name);
  const validateMutation = useValidateOneTool(tool.name);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  if (!diagnostics) {
    return <p className="text-sm text-muted-foreground">Diagnostics are unavailable.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm" onClick={() => healthMutation.mutate()} disabled={healthMutation.isPending}>
          <ShieldCheck className="h-4 w-4" /> Run Health Check
        </Button>
        <Button variant="outline" size="sm" onClick={() => validateMutation.mutate()} disabled={validateMutation.isPending}>
          <RefreshCw className={validateMutation.isPending ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Validate
        </Button>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={isFetching ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Re-run Diagnostics
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <DiagRow label="Executable" value={diagnostics.binary_names.join(", ") || "None declared"} mono />
        <DiagRow label="Resolved path" value={diagnostics.resolved_path ?? "Not found"} mono />
        <DiagRow label="Detection method" value={DETECTION_METHOD_LABEL[diagnostics.detection_method] ?? diagnostics.detection_method} />
        <DiagRow label="Custom executable path" value={diagnostics.custom_executable_path ?? "Not configured"} mono />
        <DiagRow label="Version command" value={diagnostics.version_command ? diagnostics.version_command.join(" ") : "N/A"} mono />
        <DiagRow label="Detected version" value={diagnostics.detected_version ?? "Undetermined"} />
      </div>

      <div className="rounded-xl border border-border/60 bg-secondary/25 p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Raw version output</p>
        <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-all font-mono text-xs text-foreground">
          {diagnostics.raw_version_output || "(no output captured)"}
        </pre>
      </div>

      <div className="rounded-xl border border-border/60 bg-secondary/25 p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Health check output</p>
        <p className="mt-2 text-sm text-foreground">{diagnostics.health_message ?? "No health check has been run yet."}</p>
      </div>

      <div className="rounded-xl border border-border/60 bg-secondary/25 p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">PATH</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {diagnostics.path_directories.length === 0 && <p className="text-sm text-muted-foreground">Empty</p>}
          {diagnostics.path_directories.map((dir, index) => (
            // PATH commonly contains genuine duplicate directories (observed directly on this
            // machine) -- the directory string alone is not a unique React key.
            <Badge key={`${index}-${dir}`} variant="outline" className="font-mono">
              {dir}
            </Badge>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-border/60 bg-secondary/25 p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Environment variables (relevant only)</p>
        {Object.keys(diagnostics.environment_variables).length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">None set.</p>
        ) : (
          <dl className="mt-2 space-y-1">
            {Object.entries(diagnostics.environment_variables).map(([key, value]) => (
              <div key={key} className="flex gap-2 font-mono text-xs">
                <dt className="shrink-0 text-muted-foreground">{key}=</dt>
                <dd className="break-all text-foreground">{value}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      <ValidationPanel errors={diagnostics.validation_errors} warnings={diagnostics.validation_warnings} />
    </div>
  );
}

function DiagRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-xl border border-border/60 bg-secondary/25 p-3">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={`mt-1 text-sm text-foreground ${mono ? "break-all font-mono" : ""}`}>{value}</p>
    </div>
  );
}

function ValidationPanel({ errors, warnings }: { errors: string[]; warnings: string[] }) {
  return (
    <div className="rounded-xl border border-border/60 bg-secondary/25 p-4">
      <div className="flex items-center gap-2">
        <Badge variant={errors.length === 0 ? "success" : "destructive"}>{errors.length === 0 ? "Valid" : "Invalid"}</Badge>
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
      {errors.length === 0 && warnings.length === 0 && <p className="mt-2 text-sm text-muted-foreground">No issues found.</p>}
    </div>
  );
}
