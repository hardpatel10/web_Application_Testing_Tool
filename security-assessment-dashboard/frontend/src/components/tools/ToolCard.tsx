import { Wrench } from "lucide-react";

import { ToolOverallStatusBadge } from "@/components/tools/ToolOverallStatusBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ToolSummary } from "@/types/tool";

interface ToolCardProps {
  tool: ToolSummary;
  onOpenDetails: (name: string) => void;
}

export function ToolCard({ tool, onOpenDetails }: ToolCardProps) {
  return (
    <Card
      className="cursor-pointer p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-border"
      onClick={() => onOpenDetails(tool.name)}
    >
      <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0 p-0">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-border/70 bg-secondary/55 text-primary">
            <Wrench className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base">{tool.display_name}</CardTitle>
            <p className="text-xs text-muted-foreground">{tool.version ? `v${tool.version}` : "Version unknown"}</p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 p-0 pt-4">
        <div className="flex flex-wrap gap-1.5">
          <ToolOverallStatusBadge status={tool.overall_status} />
        </div>
        <p className="text-xs text-muted-foreground">
          Targets: {tool.supported_targets.join(", ") || "—"}
        </p>
      </CardContent>
    </Card>
  );
}
