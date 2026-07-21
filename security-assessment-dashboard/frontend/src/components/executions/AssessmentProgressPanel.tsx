import { ProgressBar } from "@/components/executions/ProgressBar";
import { Card } from "@/components/ui/card";
import { useAssessmentProgress } from "@/hooks/useExecutions";

export function AssessmentProgressPanel({ assessmentId }: { assessmentId: string }) {
  const { data: progress } = useAssessmentProgress(assessmentId, { poll: true });
  if (!progress) return null;

  const finished = progress.completed + progress.failed + progress.cancelled + progress.timeout + progress.skipped;

  return (
    <Card className="space-y-4 p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-foreground">Execution progress</p>
        <span className="text-sm text-muted-foreground">
          {progress.percent_complete}% ({finished}/{progress.total})
        </span>
      </div>
      <ProgressBar value={progress.percent_complete} />
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
        <StatTile label="Running" value={progress.running} />
        <StatTile label="Queued" value={progress.pending + progress.queued + progress.preparing} />
        <StatTile label="Completed" value={progress.completed} />
        <StatTile label="Failed" value={progress.failed + progress.timeout} />
        <StatTile label="Cancelled" value={progress.cancelled} />
      </div>
      {progress.current_jobs.length > 0 && (
        <div className="space-y-1 border-t border-border/60 pt-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Currently running</p>
          {progress.current_jobs.map((job) => (
            <p key={job.id} className="text-sm text-foreground">
              <span className="capitalize">{job.tool_name}</span> → <span className="font-mono">{job.target_value}</span>
            </p>
          ))}
        </div>
      )}
    </Card>
  );
}

function StatTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-xl border border-border/60 bg-secondary/25 p-3 text-center">
      <p className="text-lg font-semibold text-foreground">{value}</p>
      <p className="text-[0.65rem] uppercase tracking-wide text-muted-foreground">{label}</p>
    </div>
  );
}
