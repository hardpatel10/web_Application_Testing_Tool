import { FileDown, FileText } from "lucide-react";
import { toast } from "sonner";

import { EmptyState } from "@/components/common/EmptyState";
import { JobStatusBadge } from "@/components/executions/JobStatusBadge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useJobRawOutput, useJobs } from "@/hooks/useExecutions";
import { ApiError } from "@/services/api-client";
import type { Job } from "@/types/execution";

/** Flat, download-focused view of every completed execution's raw tool output for one
 * assessment -- complements the interactive Executions tab rather than duplicating it. */
export function AssessmentRawResultsPanel({ assessmentId }: { assessmentId: string }) {
  const { data: jobs, isLoading } = useJobs({ assessment_id: assessmentId, status: "completed", sort_by: "created_at", sort_desc: true });

  if (isLoading) return <Skeleton className="h-40 w-full" />;

  if (!jobs || jobs.length === 0) {
    return (
      <EmptyState
        title="No raw results yet"
        description="Raw tool output becomes available here once an execution completes."
        icon={<FileText className="h-5 w-5" />}
      />
    );
  }

  return (
    <div className="space-y-2">
      {jobs.map((job) => (
        <RawResultRow key={job.id} job={job} />
      ))}
    </div>
  );
}

function RawResultRow({ job }: { job: Job }) {
  const rawOutputQuery = useJobRawOutput(job.id);

  async function handleDownload() {
    const result = await rawOutputQuery.refetch();
    if (result.error) {
      toast.error(result.error instanceof ApiError ? result.error.message : "Failed to fetch raw output.");
      return;
    }
    const rawOutput = result.data;
    if (!rawOutput?.content) {
      toast.error("No raw output recorded for this execution.");
      return;
    }
    const blob = new Blob([rawOutput.content], { type: "application/xml" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${job.tool_name}-${job.id}.${rawOutput.format}`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border/60 bg-secondary/25 p-3 text-sm">
      <span className="font-medium capitalize text-foreground">{job.tool_name}</span>
      <span className="font-mono text-muted-foreground">{job.target_value}</span>
      <JobStatusBadge status={job.status} />
      <span className="text-xs text-muted-foreground">{new Date(job.created_at).toLocaleString()}</span>
      <Button variant="outline" size="sm" className="ml-auto" disabled={rawOutputQuery.isFetching} onClick={handleDownload}>
        <FileDown className="h-4 w-4" /> Download
      </Button>
    </div>
  );
}
