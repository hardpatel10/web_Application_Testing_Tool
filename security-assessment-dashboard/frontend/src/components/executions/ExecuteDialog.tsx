import { Play } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useExecuteAssessment } from "@/hooks/useExecutions";
import { useScanProfiles } from "@/hooks/useScanProfiles";
import { useTargets } from "@/hooks/useTargets";
import { useTools } from "@/hooks/useTools";

interface ExecuteDialogProps {
  assessmentId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ExecuteDialog({ assessmentId, open, onOpenChange }: ExecuteDialogProps) {
  const { data: tools } = useTools();
  const { data: targetsPage } = useTargets(assessmentId, { page_size: 200, enabled: true });
  const executeMutation = useExecuteAssessment(assessmentId);

  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [selectedTargetIds, setSelectedTargetIds] = useState<string[] | "all">("all");
  const [nmapProfileId, setNmapProfileId] = useState<string | null>(null);

  const runnableTools = (tools ?? []).filter((tool) => tool.is_installed && tool.enabled);
  const targets = targetsPage?.items ?? [];
  const nmapSelected = selectedTools.includes("nmap");
  const { data: nmapProfiles } = useScanProfiles("nmap", undefined, { enabled: nmapSelected });

  // Reset selections each time the dialog is (re-)opened for a fresh run.
  useEffect(() => {
    if (open) {
      setSelectedTools([]);
      setSelectedTargetIds("all");
      setNmapProfileId(null);
    }
  }, [open]);

  // Default to the "service_detection" profile (matches the plugin's own
  // built-in default) the first time Nmap's profile list loads for this run.
  useEffect(() => {
    if (nmapSelected && nmapProfiles && nmapProfiles.length > 0 && nmapProfileId === null) {
      const fallback = nmapProfiles.find((profile) => profile.id === "service_detection") ?? nmapProfiles[0];
      setNmapProfileId(fallback.id);
    }
  }, [nmapSelected, nmapProfiles, nmapProfileId]);

  function toggleTool(name: string) {
    setSelectedTools((previous) => (previous.includes(name) ? previous.filter((n) => n !== name) : [...previous, name]));
  }

  function toggleTarget(id: string) {
    setSelectedTargetIds((previous) => {
      const current = previous === "all" ? targets.map((target) => target.id) : previous;
      return current.includes(id) ? current.filter((t) => t !== id) : [...current, id];
    });
  }

  function handleSubmit() {
    if (selectedTools.length === 0) return;
    executeMutation.mutate(
      {
        tool_names: selectedTools,
        target_ids: selectedTargetIds === "all" ? null : selectedTargetIds,
        tool_options: nmapSelected && nmapProfileId ? { nmap: { profile_id: nmapProfileId } } : undefined,
      },
      { onSuccess: () => onOpenChange(false) },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Run tools</DialogTitle>
          <DialogDescription>Select which installed, enabled tools to run against which enabled targets.</DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          <div>
            <p className="mb-2 text-sm font-medium text-foreground">Tools</p>
            {runnableTools.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No installed, enabled tools. Visit Tool Management and run discovery first.
              </p>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {runnableTools.map((tool) => (
                  <label
                    key={tool.name}
                    className="flex items-center gap-2 rounded-lg border border-border/60 bg-secondary/25 px-3 py-2 text-sm text-foreground"
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-border accent-primary"
                      checked={selectedTools.includes(tool.name)}
                      onChange={() => toggleTool(tool.name)}
                    />
                    {tool.display_name}
                  </label>
                ))}
              </div>
            )}
          </div>

          {nmapSelected && (
            <div>
              <p className="mb-2 text-sm font-medium text-foreground">Nmap scan profile</p>
              {nmapProfiles === undefined ? (
                <p className="text-sm text-muted-foreground">Loading profiles…</p>
              ) : nmapProfiles.length === 0 ? (
                <p className="text-sm text-muted-foreground">No scan profiles available.</p>
              ) : (
                <Select value={nmapProfileId ?? undefined} onValueChange={setNmapProfileId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Choose a profile…" />
                  </SelectTrigger>
                  <SelectContent>
                    {nmapProfiles.map((profile) => (
                      <SelectItem key={profile.id} value={profile.id}>
                        {profile.name} — {profile.estimated_duration}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
          )}

          <div>
            <div className="mb-2 flex items-center justify-between">
              <p className="text-sm font-medium text-foreground">Targets ({targets.length} enabled)</p>
              {selectedTargetIds !== "all" && (
                <Button variant="ghost" size="sm" onClick={() => setSelectedTargetIds("all")}>
                  Select all
                </Button>
              )}
            </div>
            {targets.length === 0 ? (
              <p className="text-sm text-muted-foreground">No enabled targets on this assessment.</p>
            ) : (
              <div className="max-h-48 space-y-1 overflow-y-auto">
                {targets.map((target) => {
                  const checked = selectedTargetIds === "all" || selectedTargetIds.includes(target.id);
                  return (
                    <label
                      key={target.id}
                      className="flex items-center gap-2 rounded-lg border border-border/60 bg-secondary/25 px-3 py-2 text-sm text-foreground"
                    >
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-border accent-primary"
                        checked={checked}
                        onChange={() => toggleTarget(target.id)}
                      />
                      <span className="font-mono">{target.target_value}</span>
                    </label>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={selectedTools.length === 0 || targets.length === 0 || executeMutation.isPending}>
            <Play className="h-4 w-4" /> Run
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
