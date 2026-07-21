import { Play } from "lucide-react";
import { useMemo, useState } from "react";

import { AssessmentProgressPanel } from "@/components/executions/AssessmentProgressPanel";
import { ExecuteDialog } from "@/components/executions/ExecuteDialog";
import { JobDetailsDialog } from "@/components/executions/JobDetailsDialog";
import { JobsTable } from "@/components/executions/JobsTable";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useAssessments } from "@/hooks/useAssessments";
import { useJobs } from "@/hooks/useExecutions";
import { ACTIVE_JOB_STATUSES } from "@/types/execution";

export default function Executions() {
  const { data: assessmentsPage, isLoading: assessmentsLoading } = useAssessments({ page_size: 100, sort_by: "name", sort_dir: "asc" });
  const assessments = assessmentsPage?.items ?? [];

  const [assessmentId, setAssessmentId] = useState<string>("");
  const [executeOpen, setExecuteOpen] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const jobsParams = useMemo(() => (assessmentId ? { assessment_id: assessmentId } : undefined), [assessmentId]);
  const { data: jobs, isLoading: jobsLoading } = useJobs(jobsParams, { poll: true });

  const activeJobs = (jobs ?? []).filter((job) => ACTIVE_JOB_STATUSES.includes(job.status));
  const historyJobs = (jobs ?? []).filter((job) => !ACTIVE_JOB_STATUSES.includes(job.status));

  return (
    <div className="space-y-7">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-primary/80">Orchestration</p>
          <h1 className="text-4xl font-semibold tracking-normal text-foreground">Executions</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Plan, queue, and monitor tool runs. Every job is one tool against one target, executed locally.
          </p>
        </div>
        <Button onClick={() => setExecuteOpen(true)} disabled={!assessmentId}>
          <Play className="h-4 w-4" /> Run tools
        </Button>
      </div>

      <Card className="p-5">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Assessment</p>
        {assessmentsLoading ? (
          <Skeleton className="h-10 w-72" />
        ) : (
          <Select value={assessmentId} onValueChange={setAssessmentId}>
            <SelectTrigger className="w-full sm:w-96">
              <SelectValue placeholder="Select an assessment…" />
            </SelectTrigger>
            <SelectContent>
              {assessments.map((assessment) => (
                <SelectItem key={assessment.id} value={assessment.id}>
                  {assessment.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </Card>

      {assessmentId && <AssessmentProgressPanel assessmentId={assessmentId} />}

      {!assessmentId && (
        <EmptyState
          title="Select an assessment to get started"
          description="Choose an assessment above to view its jobs and run tools against its targets."
        />
      )}

      {assessmentId && (
        <>
          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-foreground">Running &amp; queued</h2>
            {jobsLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : (
              <JobsTable jobs={activeJobs} onSelect={setSelectedJobId} emptyMessage="Nothing running or queued." />
            )}
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-foreground">History</h2>
            {jobsLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : (
              <JobsTable jobs={historyJobs} onSelect={setSelectedJobId} emptyMessage="No completed, failed, cancelled, or skipped jobs yet." />
            )}
          </section>
        </>
      )}

      {assessmentId && <ExecuteDialog assessmentId={assessmentId} open={executeOpen} onOpenChange={setExecuteOpen} />}
      <JobDetailsDialog jobId={selectedJobId} onOpenChange={(open) => !open && setSelectedJobId(null)} />
    </div>
  );
}
