import { ArrowLeft, Copy, Download, FileUp, ListChecks, Plus, RotateCcw, Search, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { AssessmentAssetsPanel } from "@/components/assessments/AssessmentAssetsPanel";
import { AssessmentExecutionsPanel } from "@/components/assessments/AssessmentExecutionsPanel";
import { AssessmentFindingsPanel } from "@/components/assessments/AssessmentFindingsPanel";
import { AssessmentFormDialog } from "@/components/assessments/AssessmentFormDialog";
import { AssessmentRawResultsPanel } from "@/components/assessments/AssessmentRawResultsPanel";
import { AssessmentReportsPanel } from "@/components/assessments/AssessmentReportsPanel";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { EmptyState } from "@/components/common/EmptyState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { BulkImportDialog } from "@/components/targets/BulkImportDialog";
import { TargetFormDialog } from "@/components/targets/TargetFormDialog";
import { TargetTable } from "@/components/targets/TargetTable";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { PaginationControls } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useArchiveAssessment,
  useAssessment,
  useAssessmentHistory,
  useDeleteAssessment,
  useDuplicateAssessment,
  useRestoreAssessment,
} from "@/hooks/useAssessments";
import { useTargets } from "@/hooks/useTargets";
import { downloadTargets } from "@/services/targets-api";

const TARGET_PAGE_SIZE = 50;

export default function AssessmentDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const assessmentId = id ?? "";

  const { data: assessment, isLoading, isError } = useAssessment(assessmentId);

  const [targetSearch, setTargetSearch] = useState("");
  const [targetPage, setTargetPage] = useState(1);
  const targetsQuery = useTargets(assessmentId, {
    search: targetSearch || undefined,
    page: targetPage,
    page_size: TARGET_PAGE_SIZE,
    sort_by: "target_value",
    sort_dir: "asc",
  });

  const [historyPage, setHistoryPage] = useState(1);
  const historyQuery = useAssessmentHistory(assessmentId, historyPage);

  const archiveMutation = useArchiveAssessment();
  const restoreMutation = useRestoreAssessment();
  const duplicateMutation = useDuplicateAssessment();
  const deleteMutation = useDeleteAssessment();
  const [confirmAction, setConfirmAction] = useState<"delete" | "archive" | null>(null);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (isError || !assessment) {
    return (
      <EmptyState
        title="Assessment not found"
        description="It may have been deleted."
        action={
          <Button variant="outline" onClick={() => navigate("/assessments")}>
            Back to assessments
          </Button>
        }
        icon={<ListChecks className="h-5 w-5" />}
      />
    );
  }

  function handleConfirm() {
    if (!assessment) return;
    if (confirmAction === "delete") {
      deleteMutation.mutate(assessment.id, { onSuccess: () => navigate("/assessments") });
    } else if (confirmAction === "archive") {
      archiveMutation.mutate(assessment.id);
    }
    setConfirmAction(null);
  }

  return (
    <div className="space-y-7">
      <div className="rounded-3xl border border-border/70 bg-card/70 p-6 shadow-[0_24px_100px_-60px_rgba(0,0,0,0.95)] backdrop-blur-xl">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="space-y-2">
            <Link to="/assessments" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
              <ArrowLeft className="h-4 w-4" /> Back to assessments
            </Link>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-4xl font-semibold tracking-normal text-foreground">{assessment.name}</h1>
              <StatusBadge status={assessment.status} />
            </div>
            {assessment.description && <p className="max-w-2xl text-sm leading-6 text-muted-foreground">{assessment.description}</p>}
            {assessment.tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {assessment.tags.map((tag) => (
                  <Badge key={tag} variant="outline">
                    {tag}
                  </Badge>
                ))}
              </div>
            )}
          </div>

          <div className="flex shrink-0 flex-wrap gap-2">
            <AssessmentFormDialog mode="edit" assessment={assessment} trigger={<Button variant="outline">Edit</Button>} />
            {assessment.status === "archived" ? (
              <Button variant="outline" onClick={() => restoreMutation.mutate(assessment.id)}>
                <RotateCcw className="h-4 w-4" /> Restore
              </Button>
            ) : (
              <Button variant="outline" onClick={() => setConfirmAction("archive")}>
                <RotateCcw className="h-4 w-4" /> Archive
              </Button>
            )}
            <Button variant="outline" onClick={() => duplicateMutation.mutate({ id: assessment.id })}>
              <Copy className="h-4 w-4" /> Duplicate
            </Button>
            <Button variant="destructive" onClick={() => setConfirmAction("delete")}>
              <Trash2 className="h-4 w-4" /> Delete
            </Button>
          </div>
        </div>
      </div>

      <Tabs defaultValue="targets">
        <TabsList className="w-full justify-start overflow-x-auto sm:w-auto">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="targets">Targets ({assessment.target_count})</TabsTrigger>
          <TabsTrigger value="executions">Executions</TabsTrigger>
          <TabsTrigger value="findings">Findings</TabsTrigger>
          <TabsTrigger value="assets">Assets Discovered</TabsTrigger>
          <TabsTrigger value="raw-results">Raw Results</TabsTrigger>
          <TabsTrigger value="reports">Reports</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <Card>
            <CardContent className="grid grid-cols-2 gap-4 pt-6 text-sm sm:grid-cols-3 lg:grid-cols-4">
              <Field label="Type" value={assessment.assessment_type.replace("_", " ")} />
              <Field label="Status" value={assessment.status} />
              <Field label="Targets" value={String(assessment.target_count)} />
              <Field label="Started" value={assessment.started_at ? new Date(assessment.started_at).toLocaleString() : "-"} />
              <Field label="Completed" value={assessment.completed_at ? new Date(assessment.completed_at).toLocaleString() : "-"} />
              <Field label="Created" value={new Date(assessment.created_at).toLocaleString()} />
              <Field label="Last Modified" value={new Date(assessment.updated_at).toLocaleString()} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="targets" className="space-y-4">
          <div className="rounded-2xl border border-border/70 bg-card/70 p-3 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="relative min-w-[240px] flex-1">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={targetSearch}
                  onChange={(event) => {
                    setTargetSearch(event.target.value);
                    setTargetPage(1);
                  }}
                  placeholder="Search targets..."
                  className="pl-9"
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" onClick={() => downloadTargets(assessment.id, "csv")}>
                  <Download className="h-4 w-4" /> Export CSV
                </Button>
                <BulkImportDialog
                  assessmentId={assessment.id}
                  trigger={
                    <Button variant="outline">
                      <FileUp className="h-4 w-4" /> Bulk Import
                    </Button>
                  }
                />
                <TargetFormDialog
                  assessmentId={assessment.id}
                  mode="create"
                  trigger={
                    <Button>
                      <Plus className="h-4 w-4" /> Add Target
                    </Button>
                  }
                />
              </div>
            </div>
          </div>

          {targetsQuery.isLoading && <Skeleton className="h-40 w-full" />}

          {!targetsQuery.isLoading && targetsQuery.data && targetsQuery.data.items.length === 0 && (
            <EmptyState
              title={targetSearch ? "No targets match your search" : "No targets yet"}
              description={
                targetSearch
                  ? "Try a different search term to reveal matching targets."
                  : "Add a target or bulk-import a list to start shaping the assessment scope."
              }
              action={
                !targetSearch && (
                  <TargetFormDialog assessmentId={assessment.id} mode="create" trigger={<Button>Add Target</Button>} />
                )
              }
              tip="Targets added here will populate the working table with type, value, notes, enabled state, and actions."
              icon={<ListChecks className="h-5 w-5" />}
            />
          )}

          {!targetsQuery.isLoading && targetsQuery.data && targetsQuery.data.items.length > 0 && (
            <div className="space-y-4 rounded-2xl border border-border/70 bg-card/70 p-4 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
              <TargetTable assessmentId={assessment.id} targets={targetsQuery.data.items} />
              <PaginationControls
                page={targetsQuery.data.page}
                totalPages={targetsQuery.data.total_pages}
                total={targetsQuery.data.total}
                pageSize={targetsQuery.data.page_size}
                onPageChange={setTargetPage}
              />
            </div>
          )}
        </TabsContent>

        <TabsContent value="executions">
          <AssessmentExecutionsPanel assessmentId={assessment.id} />
        </TabsContent>

        <TabsContent value="findings">
          <AssessmentFindingsPanel assessmentId={assessment.id} />
        </TabsContent>

        <TabsContent value="assets">
          <AssessmentAssetsPanel assessmentId={assessment.id} />
        </TabsContent>

        <TabsContent value="raw-results">
          <AssessmentRawResultsPanel assessmentId={assessment.id} />
        </TabsContent>

        <TabsContent value="reports">
          <AssessmentReportsPanel />
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          {historyQuery.isLoading && <Skeleton className="h-40 w-full" />}
          {!historyQuery.isLoading && historyQuery.data && historyQuery.data.items.length === 0 && (
            <EmptyState
              title="No activity yet"
              description="Assessment updates, target changes, and lifecycle events will appear here once work begins."
              tip="This history feed is reserved for real backend events."
              icon={<ListChecks className="h-5 w-5" />}
            />
          )}
          {!historyQuery.isLoading && historyQuery.data && historyQuery.data.items.length > 0 && (
            <div className="space-y-4 rounded-2xl border border-border/70 bg-card/70 p-4 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
              <ul className="space-y-3">
                {historyQuery.data.items.map((entry) => (
                  <li key={entry.id} className="flex flex-wrap items-start gap-3 rounded-xl border border-border/50 bg-secondary/25 p-3 text-sm">
                    <span className="w-40 shrink-0 text-muted-foreground">{new Date(entry.created_at).toLocaleString()}</span>
                    <Badge variant="outline" className="h-fit shrink-0 capitalize">
                      {entry.event_type.replace(/_/g, " ")}
                    </Badge>
                    <span className="text-foreground">{entry.message}</span>
                  </li>
                ))}
              </ul>
              <PaginationControls
                page={historyQuery.data.page}
                totalPages={historyQuery.data.total_pages}
                total={historyQuery.data.total}
                pageSize={historyQuery.data.page_size}
                onPageChange={setHistoryPage}
              />
            </div>
          )}
        </TabsContent>
      </Tabs>

      <ConfirmDialog
        open={confirmAction !== null}
        onOpenChange={(open) => !open && setConfirmAction(null)}
        title={confirmAction === "delete" ? "Delete assessment?" : "Archive assessment?"}
        description={
          confirmAction === "delete"
            ? `"${assessment.name}" will be hidden from the assessment list. Its on-disk data is not deleted.`
            : `"${assessment.name}" will be moved to Archived. You can restore it later.`
        }
        confirmLabel={confirmAction === "delete" ? "Delete" : "Archive"}
        pending={deleteMutation.isPending || archiveMutation.isPending}
        onConfirm={handleConfirm}
      />
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border/60 bg-secondary/30 p-4">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      <p className="mt-2 capitalize text-foreground">{value}</p>
    </div>
  );
}
