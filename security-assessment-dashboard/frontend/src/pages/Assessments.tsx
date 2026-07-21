import { ClipboardList, Filter, Plus, Search, SlidersHorizontal } from "lucide-react";
import { useState } from "react";

import { AssessmentFormDialog } from "@/components/assessments/AssessmentFormDialog";
import { AssessmentTable } from "@/components/assessments/AssessmentTable";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PaginationControls } from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useAssessments } from "@/hooks/useAssessments";
import { ASSESSMENT_STATUS_OPTIONS, ASSESSMENT_TYPE_OPTIONS, type AssessmentStatus, type AssessmentType } from "@/types/assessment";

const PAGE_SIZE = 20;

export default function Assessments() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<AssessmentStatus | "all">("all");
  const [assessmentType, setAssessmentType] = useState<AssessmentType | "all">("all");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useAssessments({
    search: search || undefined,
    status: status === "all" ? undefined : status,
    assessment_type: assessmentType === "all" ? undefined : assessmentType,
    sort_by: "created_at",
    sort_dir: "desc",
    page,
    page_size: PAGE_SIZE,
  });

  const hasFilters = Boolean(search) || status !== "all" || assessmentType !== "all";

  function clearFilters() {
    setSearch("");
    setStatus("all");
    setAssessmentType("all");
    setPage(1);
  }

  return (
    <div className="space-y-7">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-primary/80">Engagements</p>
          <h1 className="text-4xl font-semibold tracking-normal text-foreground">Assessments</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Create and track security assessment engagements without losing the shape of the work.
          </p>
        </div>
        <AssessmentFormDialog
          mode="create"
          trigger={
            <Button>
              <Plus className="h-4 w-4" />
              New Assessment
            </Button>
          }
        />
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/70 p-3 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[240px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
              placeholder="Search by name or description..."
              className="pl-9"
            />
          </div>
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            <SlidersHorizontal className="h-4 w-4" />
            Filters
          </div>
          <Select
            value={status}
            onValueChange={(value) => {
              setStatus(value as AssessmentStatus | "all");
              setPage(1);
            }}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              {ASSESSMENT_STATUS_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={assessmentType}
            onValueChange={(value) => {
              setAssessmentType(value as AssessmentType | "all");
              setPage(1);
            }}
          >
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              {ASSESSMENT_TYPE_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {isLoading && (
        <div className="space-y-3 rounded-2xl border border-border/70 bg-card/60 p-4">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      )}

      {isError && (
        <EmptyState
          title="Couldn't load assessments"
          description="Something went wrong talking to the backend. Try refreshing."
          icon={<Filter className="h-5 w-5" />}
        />
      )}

      {!isLoading && !isError && data && data.items.length === 0 && (
        <EmptyState
          title={hasFilters ? "No assessments match your filters" : "No assessments yet"}
          description={
            hasFilters
              ? "Try a different search, status, or assessment type to widen the workspace."
              : "Create your first assessment to define scope, add targets, and begin collecting activity."
          }
          action={!hasFilters && <AssessmentFormDialog mode="create" trigger={<Button>Create Assessment</Button>} />}
          secondaryAction={hasFilters ? <Button variant="outline" onClick={clearFilters}>Clear Filters</Button> : undefined}
          tip={
            hasFilters
              ? "Filtered results will appear here as soon as matching assessments exist."
              : "Once assessments exist, this page becomes your project index with statuses, tags, target counts, and quick actions."
          }
          icon={<ClipboardList className="h-5 w-5" />}
        />
      )}

      {!isLoading && !isError && data && data.items.length > 0 && (
        <div className="space-y-4 rounded-2xl border border-border/70 bg-card/70 p-4 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
          <AssessmentTable assessments={data.items} />
          <PaginationControls
            page={data.page}
            totalPages={data.total_pages}
            total={data.total}
            pageSize={data.page_size}
            onPageChange={setPage}
          />
        </div>
      )}
    </div>
  );
}
