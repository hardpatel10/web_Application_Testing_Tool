import { Copy, MoreHorizontal, Pencil, RotateCcw, Trash2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { AssessmentFormDialog } from "@/components/assessments/AssessmentFormDialog";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useArchiveAssessment, useDeleteAssessment, useDuplicateAssessment, useRestoreAssessment } from "@/hooks/useAssessments";
import type { Assessment } from "@/types/assessment";

interface AssessmentTableProps {
  assessments: Assessment[];
}

type PendingAction = { assessment: Assessment; kind: "delete" | "archive" } | null;

export function AssessmentTable({ assessments }: AssessmentTableProps) {
  const navigate = useNavigate();
  const archiveMutation = useArchiveAssessment();
  const restoreMutation = useRestoreAssessment();
  const duplicateMutation = useDuplicateAssessment();
  const deleteMutation = useDeleteAssessment();
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);

  const isConfirmPending = archiveMutation.isPending || deleteMutation.isPending;

  function handleConfirm() {
    if (!pendingAction) return;
    if (pendingAction.kind === "delete") {
      deleteMutation.mutate(pendingAction.assessment.id);
    } else {
      archiveMutation.mutate(pendingAction.assessment.id);
    }
    setPendingAction(null);
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Targets</TableHead>
            <TableHead>Tags</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="w-10" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {assessments.map((assessment) => (
            <TableRow
              key={assessment.id}
              className="cursor-pointer"
              onClick={() => navigate(`/assessments/${assessment.id}`)}
            >
              <TableCell className="font-medium text-foreground">{assessment.name}</TableCell>
              <TableCell className="capitalize text-muted-foreground">
                {assessment.assessment_type.replace("_", " ")}
              </TableCell>
              <TableCell>
                <StatusBadge status={assessment.status} />
              </TableCell>
              <TableCell>{assessment.target_count}</TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-1">
                  {assessment.tags.map((tag) => (
                    <Badge key={tag} variant="outline">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </TableCell>
              <TableCell className="text-muted-foreground">{new Date(assessment.created_at).toLocaleDateString()}</TableCell>
              <TableCell onClick={(event) => event.stopPropagation()}>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" aria-label="Assessment actions">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <AssessmentFormDialog
                      mode="edit"
                      assessment={assessment}
                      trigger={
                        <DropdownMenuItem onSelect={(event) => event.preventDefault()}>
                          <Pencil className="h-4 w-4" />
                          Edit
                        </DropdownMenuItem>
                      }
                    />
                    {assessment.status === "archived" ? (
                      <DropdownMenuItem onClick={() => restoreMutation.mutate(assessment.id)}>
                        <RotateCcw className="h-4 w-4" />
                        Restore
                      </DropdownMenuItem>
                    ) : (
                      <DropdownMenuItem onClick={() => setPendingAction({ assessment, kind: "archive" })}>
                        <RotateCcw className="h-4 w-4" />
                        Archive
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuItem onClick={() => duplicateMutation.mutate({ id: assessment.id })}>
                      <Copy className="h-4 w-4" />
                      Duplicate
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem destructive onClick={() => setPendingAction({ assessment, kind: "delete" })}>
                      <Trash2 className="h-4 w-4" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <ConfirmDialog
        open={pendingAction !== null}
        onOpenChange={(open) => !open && setPendingAction(null)}
        title={pendingAction?.kind === "delete" ? "Delete assessment?" : "Archive assessment?"}
        description={
          pendingAction?.kind === "delete"
            ? `"${pendingAction.assessment.name}" will be hidden from the assessment list. Its on-disk data is not deleted.`
            : `"${pendingAction?.assessment.name}" will be moved to Archived. You can restore it later.`
        }
        confirmLabel={pendingAction?.kind === "delete" ? "Delete" : "Archive"}
        onConfirm={handleConfirm}
        pending={isConfirmPending}
      />
    </>
  );
}
