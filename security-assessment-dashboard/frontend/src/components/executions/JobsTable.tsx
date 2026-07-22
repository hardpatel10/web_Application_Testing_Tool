import { JobStatusBadge } from "@/components/executions/JobStatusBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { Job } from "@/types/execution";

interface JobsTableProps {
  jobs: Job[];
  onSelect: (jobId: string) => void;
  emptyMessage: string;
}

export function JobsTable({ jobs, onSelect, emptyMessage }: JobsTableProps) {
  if (jobs.length === 0) {
    return (
      <p className="rounded-2xl border border-dashed border-border/70 bg-secondary/20 p-6 text-center text-sm leading-6 text-muted-foreground">
        {emptyMessage}
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Tool</TableHead>
          <TableHead>Target</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Duration</TableHead>
          <TableHead>Retries</TableHead>
          <TableHead>Created</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {jobs.map((job) => (
          <TableRow key={job.id} className="cursor-pointer" onClick={() => onSelect(job.id)}>
            <TableCell className="font-medium capitalize text-foreground">{job.tool_name}</TableCell>
            <TableCell className="font-mono text-muted-foreground">{job.target_value}</TableCell>
            <TableCell>
              <JobStatusBadge status={job.status} />
            </TableCell>
            <TableCell className="text-muted-foreground">{job.duration != null ? `${job.duration.toFixed(2)}s` : "—"}</TableCell>
            <TableCell className="text-muted-foreground">{job.retry_count}</TableCell>
            <TableCell className="text-muted-foreground">{new Date(job.created_at).toLocaleString()}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
