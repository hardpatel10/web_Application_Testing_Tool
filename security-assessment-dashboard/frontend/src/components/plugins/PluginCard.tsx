import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePlugin, usePluginHealth } from "@/hooks/usePlugins";
import type { PluginHealthStatus } from "@/types/plugin";

const HEALTH_BADGE_VARIANT: Record<PluginHealthStatus, "success" | "warning" | "destructive" | "secondary"> = {
  healthy: "success",
  degraded: "warning",
  unhealthy: "destructive",
  not_installed: "destructive",
  unknown: "secondary",
};

interface PluginCardProps {
  pluginId: string;
}

export function PluginCard({ pluginId }: PluginCardProps) {
  const { data: plugin, isLoading, isError } = usePlugin(pluginId);
  const { data: health } = usePluginHealth(pluginId);

  if (isLoading) {
    return (
      <Card className="p-6">
        <CardHeader className="p-0">
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent className="p-0 pt-5">
          <Skeleton className="h-16 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (isError || !plugin) {
    return (
      <Card className="p-6">
        <CardHeader className="p-0">
          <CardTitle>{pluginId}</CardTitle>
        </CardHeader>
        <CardContent className="p-0 pt-5">
          <p className="text-sm text-muted-foreground">Couldn't load this plugin's detail.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="p-6 transition-all duration-200 hover:-translate-y-0.5 hover:border-border">
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0 p-0">
        <div>
          <CardTitle>{plugin.display_name}</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            v{plugin.version} by {plugin.author}
          </p>
        </div>
        <div className="flex flex-wrap justify-end gap-1.5">
          <Badge variant={plugin.config.enabled ? "success" : "secondary"}>
            {plugin.config.enabled ? "Enabled" : "Disabled"}
          </Badge>
          <Badge variant={health ? HEALTH_BADGE_VARIANT[health.status] : "secondary"}>{health?.status ?? "unknown"}</Badge>
          <Badge variant={plugin.validation_valid ? "success" : "destructive"}>
            {plugin.validation_valid ? "Valid" : "Invalid"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-5 p-0 pt-5">
        <p className="text-sm leading-6 text-muted-foreground">{plugin.description}</p>

        {!plugin.validation_valid && plugin.validation_errors.length > 0 && (
          <ul className="list-inside list-disc text-sm text-destructive">
            {plugin.validation_errors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        )}

        <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
          <Detail label="Supported targets" value={plugin.supported_targets.join(", ") || "None"} />
          <Detail label="Output formats" value={plugin.supported_output_formats.join(", ") || "None"} />
          <Detail label="Required binaries" value={plugin.required_binaries.join(", ") || "None"} />
          <div className="rounded-xl border border-border/60 bg-secondary/30 p-3">
            <p className="font-medium text-foreground">Dependencies</p>
            <p className={plugin.missing_dependencies.length > 0 ? "text-destructive" : "text-muted-foreground"}>
              {plugin.dependencies.length === 0
                ? "None"
                : plugin.missing_dependencies.length > 0
                  ? `Missing: ${plugin.missing_dependencies.join(", ")}`
                  : plugin.dependencies.join(", ")}
            </p>
          </div>
        </div>

        {health?.message && <p className="text-xs leading-5 text-muted-foreground">{health.message}</p>}
      </CardContent>
    </Card>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/60 bg-secondary/30 p-3">
      <p className="font-medium text-foreground">{label}</p>
      <p className="text-muted-foreground">{value}</p>
    </div>
  );
}
