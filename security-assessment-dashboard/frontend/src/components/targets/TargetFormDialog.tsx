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
import { useCreateTarget, useUpdateTarget, useValidateTarget } from "@/hooks/useTargets";
import { TARGET_TYPE_OPTIONS, type Target, type TargetType } from "@/types/target";

interface TargetFormDialogProps {
  assessmentId: string;
  mode: "create" | "edit";
  target?: Target;
  trigger: ReactNode;
}

export function TargetFormDialog({ assessmentId, mode, target, trigger }: TargetFormDialogProps) {
  const [open, setOpen] = useState(false);
  const [targetType, setTargetType] = useState<TargetType>(target?.target_type ?? "ipv4");
  const [targetValue, setTargetValue] = useState(target?.target_value ?? "");
  const [notes, setNotes] = useState(target?.notes ?? "");
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  const createMutation = useCreateTarget(assessmentId);
  const updateMutation = useUpdateTarget(assessmentId);
  const validateMutation = useValidateTarget(assessmentId);
  const pending = createMutation.isPending || updateMutation.isPending;

  function resetForm() {
    setTargetType(target?.target_type ?? "ipv4");
    setTargetValue(target?.target_value ?? "");
    setNotes(target?.notes ?? "");
    setValidationMessage(null);
  }

  async function handleBlur() {
    if (!targetValue.trim()) {
      setValidationMessage(null);
      return;
    }
    const result = await validateMutation.mutateAsync({ targetType, targetValue });
    setValidationMessage(result.valid ? null : result.message);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (mode === "create") {
      await createMutation.mutateAsync({ target_type: targetType, target_value: targetValue, notes: notes || null });
    } else if (target) {
      await updateMutation.mutateAsync({
        targetId: target.id,
        payload: { target_type: targetType, target_value: targetValue, notes: notes || null },
      });
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
          <DialogTitle>{mode === "create" ? "Add Target" : "Edit Target"}</DialogTitle>
          <DialogDescription>
            {mode === "create" ? "Add a scan target to this assessment." : "Update this target."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="target-type">Target Type</Label>
            <Select value={targetType} onValueChange={(value) => setTargetType(value as TargetType)}>
              <SelectTrigger id="target-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TARGET_TYPE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="target-value">Value</Label>
            <Input
              id="target-value"
              value={targetValue}
              onChange={(event) => setTargetValue(event.target.value)}
              onBlur={handleBlur}
              required
              maxLength={512}
              placeholder="e.g. 192.168.1.10, example.com, https://app.example.com"
            />
            {validationMessage && <p className="text-xs text-destructive">{validationMessage}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="target-notes">Notes</Label>
            <Textarea id="target-notes" value={notes} onChange={(event) => setNotes(event.target.value)} rows={2} />
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" disabled={pending}>
              {pending ? "Saving…" : mode === "create" ? "Add Target" : "Save Changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
