import { RefreshCw, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { EmptyState } from "@/components/common/EmptyState";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PaginationControls } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { useFindings, useRunCorrelation } from "@/hooks/useFindings";
import type { FindingConfidence } from "@/types/finding";

const PAGE_SIZE = 10;

const CONFIDENCE_VARIANT: Record<FindingConfidence, "success" | "default" | "secondary" | "outline"> = {
  confirmed: "success",
  high: "default",
  medium: "secondary",
  low: "outline",
};

/** Findings scoped to one assessment -- same rendering as the global Findings page, without
 * its own search/filter bar (an assessment's findings are typically few enough not to need it). */
export function AssessmentFindingsPanel({ assessmentId }: { assessmentId: string }) {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const { data, isLoading, isError } = useFindings({
    assessment_id: assessmentId, sort_by: "last_seen", sort_dir: "desc", page, page_size: PAGE_SIZE,
  });
  const runCorrelation = useRunCorrelation();

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button variant="outline" size="sm" disabled={runCorrelation.isPending} onClick={() => runCorrelation.mutate(assessmentId)}>
          <RefreshCw className={`h-4 w-4 ${runCorrelation.isPending ? "animate-spin" : ""}`} /> Run Correlation
        </Button>
      </div>

      {isLoading && <Skeleton className="h-32 w-full" />}
      {isError && <EmptyState title="Couldn't load findings" description="Something went wrong talking to the backend." icon={<ShieldAlert className="h-5 w-5" />} />}
      {!isLoading && !isError && data && data.items.length === 0 && (
        <EmptyState
          title="No findings yet"
          description="Run tools against this assessment's targets, then run correlation."
          action={
            <Button disabled={runCorrelation.isPending} onClick={() => runCorrelation.mutate(assessmentId)}>
              <RefreshCw className="h-4 w-4" /> Run Correlation
            </Button>
          }
          icon={<ShieldAlert className="h-5 w-5" />}
        />
      )}
      {!isLoading && !isError && data && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((finding) => (
            <div
              key={finding.id}
              className="cursor-pointer rounded-xl border border-border/60 bg-card/70 p-4 transition-colors hover:border-border"
              onClick={() => navigate(`/findings/${finding.id}`)}
            >
              <div className="flex flex-wrap items-center gap-2">
                <SeverityBadge severity={finding.severity} />
                <Badge variant={CONFIDENCE_VARIANT[finding.confidence]} className="capitalize">{finding.confidence} confidence</Badge>
                {finding.category && <Badge variant="outline" className="capitalize">{finding.category}</Badge>}
                <span className="font-mono text-xs text-muted-foreground">{finding.rule_id}</span>
              </div>
              <p className="mt-2 font-medium text-foreground">{finding.title}</p>
              <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                {finding.host_label && <span>{finding.host_label}</span>}
                {finding.plugin && <span className="uppercase tracking-wide">{finding.plugin}</span>}
                <span>{finding.evidence_count} evidence</span>
              </div>
            </div>
          ))}
          <PaginationControls page={data.page} totalPages={data.total_pages} total={data.total} pageSize={data.page_size} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}
