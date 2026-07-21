import { Copy, MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { useState } from "react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { TargetFormDialog } from "@/components/targets/TargetFormDialog";
import { useDeleteTarget, useDuplicateTarget, useToggleTargetEnabled } from "@/hooks/useTargets";
import type { Target } from "@/types/target";

interface TargetTableProps {
  assessmentId: string;
  targets: Target[];
}

export function TargetTable({ assessmentId, targets }: TargetTableProps) {
  const toggleMutation = useToggleTargetEnabled(assessmentId);
  const duplicateMutation = useDuplicateTarget(assessmentId);
  const deleteMutation = useDeleteTarget(assessmentId);
  const [pendingDelete, setPendingDelete] = useState<Target | null>(null);

  function handleDuplicate(target: Target) {
    if (target.target_type === "ipv4" || target.target_type === "ipv6" || target.target_type === "cidr") {
      const explicitValue = window.prompt(
        `Enter a new value to duplicate "${target.target_value}" as (IP-type targets can't be auto-duplicated):`,
      );
      if (!explicitValue) return;
      duplicateMutation.mutate({ targetId: target.id, targetValue: explicitValue });
    } else {
      duplicateMutation.mutate({ targetId: target.id });
    }
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Type</TableHead>
            <TableHead>Value</TableHead>
            <TableHead>Notes</TableHead>
            <TableHead>Enabled</TableHead>
            <TableHead className="w-10" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {targets.map((target) => (
            <TableRow key={target.id}>
              <TableCell>
                <Badge variant="outline" className="uppercase">
                  {target.target_type}
                </Badge>
              </TableCell>
              <TableCell className="font-mono text-sm">{target.target_value}</TableCell>
              <TableCell className="text-muted-foreground">{target.notes || "-"}</TableCell>
              <TableCell>
                <Switch
                  checked={target.enabled}
                  onCheckedChange={(checked) => toggleMutation.mutate({ targetId: target.id, enabled: checked })}
                  aria-label={target.enabled ? "Disable target" : "Enable target"}
                />
              </TableCell>
              <TableCell>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" aria-label="Target actions">
                      <MoreHorizontal className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <TargetFormDialog
                      assessmentId={assessmentId}
                      mode="edit"
                      target={target}
                      trigger={
                        <DropdownMenuItem onSelect={(event) => event.preventDefault()}>
                          <Pencil className="h-4 w-4" />
                          Edit
                        </DropdownMenuItem>
                      }
                    />
                    <DropdownMenuItem onClick={() => handleDuplicate(target)}>
                      <Copy className="h-4 w-4" />
                      Duplicate
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem destructive onClick={() => setPendingDelete(target)}>
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
        open={pendingDelete !== null}
        onOpenChange={(open) => !open && setPendingDelete(null)}
        title="Delete target?"
        description={`"${pendingDelete?.target_value}" will be permanently removed from this assessment.`}
        confirmLabel="Delete"
        pending={deleteMutation.isPending}
        onConfirm={() => {
          if (pendingDelete) deleteMutation.mutate(pendingDelete.id);
          setPendingDelete(null);
        }}
      />
    </>
  );
}
