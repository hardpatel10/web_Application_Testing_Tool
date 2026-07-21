import { type FormEvent, type ReactNode, useState } from "react";

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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useCreateAssessment, useUpdateAssessment } from "@/hooks/useAssessments";
import { ASSESSMENT_TYPE_OPTIONS, type Assessment, type AssessmentType } from "@/types/assessment";

interface AssessmentFormDialogProps {
  mode: "create" | "edit";
  assessment?: Assessment;
  trigger: ReactNode;
}

export function AssessmentFormDialog({ mode, assessment, trigger }: AssessmentFormDialogProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(assessment?.name ?? "");
  const [description, setDescription] = useState(assessment?.description ?? "");
  const [assessmentType, setAssessmentType] = useState<AssessmentType>(assessment?.assessment_type ?? "network");
  const [tagsInput, setTagsInput] = useState((assessment?.tags ?? []).join(", "));

  const createMutation = useCreateAssessment();
  const updateMutation = useUpdateAssessment(assessment?.id ?? "");
  const pending = createMutation.isPending || updateMutation.isPending;

  function resetForm() {
    setName(assessment?.name ?? "");
    setDescription(assessment?.description ?? "");
    setAssessmentType(assessment?.assessment_type ?? "network");
    setTagsInput((assessment?.tags ?? []).join(", "));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const tags = tagsInput
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);

    const payload = { name, description: description || null, assessment_type: assessmentType, tags };
    if (mode === "create") {
      await createMutation.mutateAsync(payload);
    } else {
      await updateMutation.mutateAsync(payload);
    }
    setOpen(false);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) resetForm();
      }}
    >
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "Create Assessment" : "Edit Assessment"}</DialogTitle>
          <DialogDescription>
            {mode === "create" ? "Start a new security assessment." : "Update this assessment's details."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="assessment-name">Name</Label>
            <Input id="assessment-name" value={name} onChange={(event) => setName(event.target.value)} required maxLength={255} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="assessment-description">Description</Label>
            <Textarea
              id="assessment-description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={3}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="assessment-type">Assessment Type</Label>
            <Select value={assessmentType} onValueChange={(value) => setAssessmentType(value as AssessmentType)}>
              <SelectTrigger id="assessment-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ASSESSMENT_TYPE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="assessment-tags">Tags</Label>
            <Input
              id="assessment-tags"
              value={tagsInput}
              onChange={(event) => setTagsInput(event.target.value)}
              placeholder="prod, client-acme, q3-2026"
            />
            <p className="text-xs text-muted-foreground">Comma-separated.</p>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" disabled={pending}>
              {pending ? "Saving…" : mode === "create" ? "Create Assessment" : "Save Changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
