import { Ban, FileDown, RotateCcw } from "lucide-react";
import { toast } from "sonner";

import { JobResultsView } from "@/components/executions/JobResultsView";
import { JobStatusBadge } from "@/components/executions/JobStatusBadge";
import { LogViewer } from "@/components/executions/LogViewer";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCancelJob, useJob, useJobRawOutput, useRetryJob } from "@/hooks/useExecutions";
import { ApiError } from "@/services/api-client";
import { ACTIVE_JOB_STATUSES, RETRIABLE_JOB_STATUSES } from "@/types/execution";

interface JobDetailsDialogProps {
  jobId: string | null;
  onOpenChange: (open: boolean) => void;
}

export function JobDetailsDialog({ jobId, onOpenChange }: JobDetailsDialogProps) {
  const { data: job, isLoading } = useJob(jobId ?? undefined, { poll: true });
  const cancelMutation = useCancelJob();
  const retryMutation = useRetryJob();
  const rawOutputQuery = useJobRawOutput(job?.id);

  const canCancel = job !== undefined && ACTIVE_JOB_STATUSES.includes(job.status);
  const canRetry = job !== undefined && RETRIABLE_JOB_STATUSES.includes(job.status);
  const isCompleted = job?.status === "completed";

  async function handleDownloadXml() {
    if (!job) return;
    const result = await rawOutputQuery.refetch();
    if (result.error) {
      toast.error(result.error instanceof ApiError ? result.error.message : "Failed to fetch raw output.");
      return;
    }
    const rawOutput = result.data;
    if (!rawOutput?.content) {
      toast.error("No raw output recorded for this job.");
      return;
    }
    const blob = new Blob([rawOutput.content], { type: "application/xml" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `job-${job.id}.${rawOutput.format}`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Dialog open={Boolean(jobId)} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        {isLoading && (
          <div className="space-y-3">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-32 w-full" />
          </div>
        )}

        {job && (
          <>
            <DialogHeader>
              <div className="flex flex-wrap items-center gap-2">
                <DialogTitle className="capitalize">{job.tool_name}</DialogTitle>
                <JobStatusBadge status={job.status} />
              </div>
              <DialogDescription className="font-mono">{job.target_value}</DialogDescription>
            </DialogHeader>

            {job.status_message && (
              <p className="rounded-xl border border-border/60 bg-secondary/25 p-3 text-sm text-muted-foreground">
                {job.status_message}
              </p>
            )}

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              <InfoTile label="Started" value={job.started_at ? new Date(job.started_at).toLocaleTimeString() : "—"} />
              <InfoTile label="Completed" value={job.completed_at ? new Date(job.completed_at).toLocaleTimeString() : "—"} />
              <InfoTile label="Duration" value={job.duration != null ? `${job.duration.toFixed(2)}s` : "—"} />
              <InfoTile label="Return code" value={job.return_code != null ? String(job.return_code) : "—"} />
              <InfoTile label="Retries" value={String(job.retry_count)} />
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={!canCancel || cancelMutation.isPending}
                onClick={() => cancelMutation.mutate(job.id)}
              >
                <Ban className="h-4 w-4" /> Cancel
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={!canRetry || retryMutation.isPending}
                onClick={() => retryMutation.mutate(job.id)}
              >
                <RotateCcw className="h-4 w-4" /> Retry
              </Button>
              <Button variant="outline" size="sm" disabled={!isCompleted || rawOutputQuery.isFetching} onClick={handleDownloadXml}>
                <FileDown className="h-4 w-4" /> Download XML
              </Button>
            </div>

            <Tabs defaultValue="log">
              <TabsList>
                <TabsTrigger value="log">Log</TabsTrigger>
                <TabsTrigger value="results">Results</TabsTrigger>
              </TabsList>
              <TabsContent value="log">
                <LogViewer jobId={job.id} isActive={ACTIVE_JOB_STATUSES.includes(job.status)} />
              </TabsContent>
              <TabsContent value="results">
                <JobResultsView jobId={job.id} enabled={isCompleted} />
              </TabsContent>
            </Tabs>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/60 bg-secondary/25 p-3">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm text-foreground">{value}</p>
    </div>
  );
}
