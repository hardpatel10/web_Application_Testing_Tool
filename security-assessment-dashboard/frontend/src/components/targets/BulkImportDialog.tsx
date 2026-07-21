import { type ChangeEvent, type ReactNode, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useBulkImportTargets } from "@/hooks/useTargets";
import type { TargetBulkImportResult } from "@/types/target";

interface BulkImportDialogProps {
  assessmentId: string;
  trigger: ReactNode;
}

export function BulkImportDialog({ assessmentId, trigger }: BulkImportDialogProps) {
  const [open, setOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<TargetBulkImportResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const importMutation = useBulkImportTargets(assessmentId);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFile(event.target.files?.[0] ?? null);
    setResult(null);
  }

  async function handleImport() {
    if (!selectedFile) return;
    const importResult = await importMutation.mutateAsync(selectedFile);
    setResult(importResult);
    setSelectedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) {
          setSelectedFile(null);
          setResult(null);
        }
      }}
    >
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Bulk Import Targets</DialogTitle>
          <DialogDescription>Upload a TXT file (one target per line) or a CSV file (target_type,target_value).</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.csv,text/plain,text/csv"
            onChange={handleFileChange}
            className="block w-full text-sm text-muted-foreground file:mr-4 file:rounded-md file:border-0 file:bg-primary file:px-4 file:py-2 file:text-sm file:font-medium file:text-primary-foreground hover:file:bg-primary/90"
          />

          {result && (
            <div className="space-y-3 rounded-md border border-border p-3">
              <div className="flex flex-wrap gap-2 text-sm">
                <Badge variant="outline">Total lines: {result.total_lines}</Badge>
                <Badge variant="success">Imported: {result.imported}</Badge>
                <Badge variant="warning">Duplicates: {result.skipped_duplicates}</Badge>
                <Badge variant="destructive">Invalid: {result.skipped_invalid}</Badge>
              </div>
              {result.errors.length > 0 && (
                <div className="max-h-48 overflow-y-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Line</TableHead>
                        <TableHead>Value</TableHead>
                        <TableHead>Reason</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {result.errors.map((error) => (
                        <TableRow key={error.line_number}>
                          <TableCell>{error.line_number}</TableCell>
                          <TableCell className="font-mono text-xs">{error.raw_value}</TableCell>
                          <TableCell className="text-xs text-muted-foreground">{error.reason}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <DialogClose asChild>
            <Button type="button" variant="outline">
              Close
            </Button>
          </DialogClose>
          <Button type="button" disabled={!selectedFile || importMutation.isPending} onClick={handleImport}>
            {importMutation.isPending ? "Importing…" : "Import"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
