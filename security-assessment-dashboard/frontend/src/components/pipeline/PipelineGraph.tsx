import { ArrowRight } from "lucide-react";
import type { ReactNode } from "react";

import { PipelineJobStatusBadge } from "@/components/pipeline/PipelineJobStatusBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePipeline } from "@/hooks/usePipeline";
import type { PipelineJob } from "@/types/pipeline";

/** Fixed 3-stage shape (Recon -> Scan -> Correlate) -- the Assessment Pipeline's actual shape,
 * not a generic graph, so a hand-rolled column layout needs no DAG library. */
export function PipelineGraph({ assessmentId }: { assessmentId: string }) {
  const { data: run, isLoading } = usePipeline(assessmentId, { poll: true });

  if (isLoading) {
    return <Skeleton className="h-48 w-full" />;
  }

  if (!run) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          No Assessment Pipeline run yet. Click "Start Assessment" to let the platform run recon and
          automatically decide which follow-up scanners make sense.
        </CardContent>
      </Card>
    );
  }

  const recon = run.jobs.find((job) => job.stage === "recon") ?? null;
  const scanJobs = run.jobs.filter((job) => job.stage === "scan");
  const correlate = run.jobs.find((job) => job.stage === "correlate") ?? null;

  const scanByHost = new Map<string, PipelineJob[]>();
  for (const job of scanJobs) {
    const key = job.host_label ?? "This host";
    scanByHost.set(key, [...(scanByHost.get(key) ?? []), job]);
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-[1fr_auto_2fr_auto_1fr]">
      <StageColumn title="Recon">{recon && <JobCard job={recon} />}</StageColumn>

      <StageArrow />

      <StageColumn title="Scan">
        {scanByHost.size === 0 ? (
          <p className="text-sm text-muted-foreground">Waiting on recon…</p>
        ) : (
          Array.from(scanByHost.entries()).map(([hostLabel, jobs]) => (
            <div key={hostLabel} className="space-y-2 rounded-xl border border-border/50 bg-secondary/10 p-3">
              <p className="font-mono text-xs text-muted-foreground">{hostLabel}</p>
              <div className="space-y-2">
                {jobs.map((job) => (
                  <JobCard key={job.id} job={job} />
                ))}
              </div>
            </div>
          ))
        )}
      </StageColumn>

      <StageArrow />

      <StageColumn title="Correlate">
        {correlate ? <JobCard job={correlate} label="Correlation Engine" /> : <p className="text-sm text-muted-foreground">Waiting on scan…</p>}
      </StageColumn>
    </div>
  );
}

function StageColumn({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</p>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function StageArrow() {
  return (
    <div className="hidden items-center justify-center pt-6 text-muted-foreground md:flex">
      <ArrowRight className="h-4 w-4" />
    </div>
  );
}

function JobCard({ job, label }: { job: PipelineJob; label?: string }) {
  return (
    <Card>
      <CardHeader className="p-3 pb-1">
        <CardTitle className="flex items-center justify-between gap-2 text-sm capitalize">
          <span>{label ?? job.tool_name ?? "Scanner"}</span>
          <PipelineJobStatusBadge status={job.status} />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1 p-3 pt-0 text-xs">
        {job.target_value && <p className="font-mono text-muted-foreground">{job.target_value}</p>}
        {job.skip_reason && <p className="text-muted-foreground">{job.skip_reason}</p>}
      </CardContent>
    </Card>
  );
}
