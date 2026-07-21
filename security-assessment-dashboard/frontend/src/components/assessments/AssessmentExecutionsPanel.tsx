import { Play } from "lucide-react";
import { useState } from "react";

import { ExecuteDialog } from "@/components/executions/ExecuteDialog";
import { JobDetailsDialog } from "@/components/executions/JobDetailsDialog";
import { JobsTable } from "@/components/executions/JobsTable";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useJobs } from "@/hooks/useExecutions";

/** Executions scoped to one assessment -- the same job list/detail machinery as the global
 * Executions page, just pre-filtered by assessment_id instead of requiring a picker. */
export function AssessmentExecutionsPanel({ assessmentId }: { assessmentId: string }) {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [executeOpen, setExecuteOpen] = useState(false);
  const { data: jobs, isLoading } = useJobs({ assessment_id: assessmentId, sort_by: "created_at", sort_desc: true }, { poll: true });

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => setExecuteOpen(true)}>
          <Play className="h-4 w-4" /> Run tools
        </Button>
      </div>

      {isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : (
        <JobsTable jobs={jobs ?? []} onSelect={setSelectedJobId} emptyMessage="No executions yet for this assessment." />
      )}

      <ExecuteDialog assessmentId={assessmentId} open={executeOpen} onOpenChange={setExecuteOpen} />
      <JobDetailsDialog jobId={selectedJobId} onOpenChange={(open) => !open && setSelectedJobId(null)} />
    </div>
  );
}
