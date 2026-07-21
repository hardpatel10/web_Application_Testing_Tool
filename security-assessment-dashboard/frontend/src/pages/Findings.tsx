import { Filter, RefreshCw, Search as SearchIcon, ShieldAlert, SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { EmptyState } from "@/components/common/EmptyState";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PaginationControls } from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useFindings, useRunCorrelation } from "@/hooks/useFindings";
import {
  FINDING_CONFIDENCE_OPTIONS,
  FINDING_SEVERITY_OPTIONS,
  FINDING_STATUS_OPTIONS,
  type FindingConfidence,
  type FindingSeverity,
  type FindingStatus,
} from "@/types/finding";

const PAGE_SIZE = 20;

const CONFIDENCE_VARIANT: Record<FindingConfidence, "success" | "default" | "secondary" | "outline"> = {
  confirmed: "success",
  high: "default",
  medium: "secondary",
  low: "outline",
};

export default function Findings() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState<FindingSeverity | "all">("all");
  const [confidence, setConfidence] = useState<FindingConfidence | "all">("all");
  const [status, setStatus] = useState<FindingStatus | "all">("all");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useFindings({
    search: search || undefined,
    severity: severity === "all" ? undefined : severity,
    confidence: confidence === "all" ? undefined : confidence,
    status: status === "all" ? undefined : status,
    sort_by: "last_seen",
    sort_dir: "desc",
    page,
    page_size: PAGE_SIZE,
  });
  const runCorrelation = useRunCorrelation();

  return (
    <div className="space-y-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-primary/80">Correlation Engine</p>
          <h1 className="text-4xl font-semibold tracking-normal text-foreground">Findings</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Correlated conclusions drawn from real observations, services, technologies, and operating systems — never a fabricated vulnerability.
          </p>
        </div>
        <Button variant="outline" disabled={runCorrelation.isPending} onClick={() => runCorrelation.mutate(undefined)}>
          <RefreshCw className={`h-4 w-4 ${runCorrelation.isPending ? "animate-spin" : ""}`} />
          Run Correlation
        </Button>
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/70 p-3 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[240px] flex-1">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search by title or description..."
              className="pl-9"
            />
          </div>
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            <SlidersHorizontal className="h-4 w-4" /> Filters
          </div>
          <Select value={severity} onValueChange={(v) => { setSeverity(v as FindingSeverity | "all"); setPage(1); }}>
            <SelectTrigger className="w-40"><SelectValue placeholder="Severity" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severities</SelectItem>
              {FINDING_SEVERITY_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={confidence} onValueChange={(v) => { setConfidence(v as FindingConfidence | "all"); setPage(1); }}>
            <SelectTrigger className="w-40"><SelectValue placeholder="Confidence" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All confidence</SelectItem>
              {FINDING_CONFIDENCE_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={status} onValueChange={(v) => { setStatus(v as FindingStatus | "all"); setPage(1); }}>
            <SelectTrigger className="w-40"><SelectValue placeholder="Status" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              {FINDING_STATUS_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {isLoading && (
        <div className="space-y-3 rounded-2xl border border-border/70 bg-card/60 p-4">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      )}
      {isError && (
        <EmptyState title="Couldn't load findings" description="Something went wrong talking to the backend." icon={<Filter className="h-5 w-5" />} />
      )}
      {!isLoading && !isError && data && data.items.length === 0 && (
        <EmptyState
          title="No findings yet"
          description="The Correlation Engine only produces a finding when a deterministic rule is actually supported by collected observations. Run a scan, then run correlation."
          action={
            <Button disabled={runCorrelation.isPending} onClick={() => runCorrelation.mutate(undefined)}>
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
              className="cursor-pointer rounded-xl border border-border/60 bg-card/70 p-4 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] transition-colors hover:border-border"
              onClick={() => navigate(`/findings/${finding.id}`)}
            >
              <div className="flex flex-wrap items-center gap-2">
                <SeverityBadge severity={finding.severity} />
                <Badge variant={CONFIDENCE_VARIANT[finding.confidence]} className="capitalize">{finding.confidence} confidence</Badge>
                {finding.category && <Badge variant="outline" className="capitalize">{finding.category}</Badge>}
                <span className="font-mono text-xs text-muted-foreground">{finding.rule_id}</span>
                <span className="ml-auto text-xs text-muted-foreground">{new Date(finding.last_seen).toLocaleString()}</span>
              </div>
              <p className="mt-2 font-medium text-foreground">{finding.title}</p>
              <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                {finding.host_label && <span>{finding.host_label}</span>}
                {finding.plugin && <span className="uppercase tracking-wide">{finding.plugin}</span>}
                <span>{finding.evidence_count} evidence</span>
                <span>{finding.observation_count} observation(s)</span>
                <span className="capitalize">{finding.status.replace("_", " ")}</span>
              </div>
            </div>
          ))}
          <PaginationControls page={data.page} totalPages={data.total_pages} total={data.total} pageSize={data.page_size} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}
