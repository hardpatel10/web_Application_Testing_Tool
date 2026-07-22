import { ChevronDown, ChevronRight, Play } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useExecuteAssessment } from "@/hooks/useExecutions";
import { useStartPipeline } from "@/hooks/usePipeline";
import { useScanProfiles } from "@/hooks/useScanProfiles";
import { useTargets } from "@/hooks/useTargets";
import { useTools } from "@/hooks/useTools";

interface ExecuteDialogProps {
  assessmentId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

//: Recommended/default profile ids each plugin falls back to on its own when no profile_id is
//: sent at all -- used only to pre-select a sensible starting point once Advanced Mode is opened,
//: never required for the simplified (non-advanced) path, which omits tool_options entirely and
//: lets each plugin's own DEFAULT_PROFILE_ID apply server-side.
const KNOWN_RECOMMENDED_PROFILE_IDS = ["intelligent_standard", "service_detection", "default_scan", "default"];

export function ExecuteDialog({ assessmentId, open, onOpenChange }: ExecuteDialogProps) {
  const [mode, setMode] = useState<"pipeline" | "manual">("pipeline");

  useEffect(() => {
    if (open) setMode("pipeline");
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        {mode === "pipeline" ? (
          <PipelineStartView assessmentId={assessmentId} onOpenChange={onOpenChange} onRunIndividually={() => setMode("manual")} />
        ) : (
          <ManualExecuteView assessmentId={assessmentId} onOpenChange={onOpenChange} onBackToPipeline={() => setMode("pipeline")} />
        )}
      </DialogContent>
    </Dialog>
  );
}

/** The default flow: no scanner selection at all -- the platform runs Nmap recon, then decides
 * which follow-up scanners make sense from what it actually discovers (the Assessment Pipeline). */
function PipelineStartView({
  assessmentId,
  onOpenChange,
  onRunIndividually,
}: {
  assessmentId: string;
  onOpenChange: (open: boolean) => void;
  onRunIndividually: () => void;
}) {
  const { data: targetsPage } = useTargets(assessmentId, { page_size: 200, enabled: true });
  const startMutation = useStartPipeline(assessmentId);
  const targets = targetsPage?.items ?? [];
  const [targetId, setTargetId] = useState<string | null>(null);
  const firstTargetId = targetsPage?.items[0]?.id;

  useEffect(() => {
    if (targetId === null && firstTargetId) setTargetId(firstTargetId);
  }, [firstTargetId, targetId]);

  return (
    <>
      <DialogHeader>
        <DialogTitle>Start Assessment</DialogTitle>
        <DialogDescription>
          Choose a target and start — the platform runs recon, then automatically decides which follow-up
          scanners make sense from what it discovers.
        </DialogDescription>
      </DialogHeader>

      <div className="space-y-3">
        <p className="text-sm font-medium text-foreground">Target</p>
        {targets.length === 0 ? (
          <p className="text-sm text-muted-foreground">No enabled targets on this assessment.</p>
        ) : (
          <Select value={targetId ?? undefined} onValueChange={setTargetId}>
            <SelectTrigger>
              <SelectValue placeholder="Choose a target…" />
            </SelectTrigger>
            <SelectContent>
              {targets.map((target) => (
                <SelectItem key={target.id} value={target.id}>
                  {target.target_value}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        <Button variant="ghost" size="sm" className="px-0 text-muted-foreground" onClick={onRunIndividually}>
          Advanced: run scanners individually instead
        </Button>
      </div>

      <DialogFooter>
        <Button variant="outline" onClick={() => onOpenChange(false)}>
          Cancel
        </Button>
        <Button
          disabled={!targetId || startMutation.isPending}
          onClick={() => targetId && startMutation.mutate({ target_id: targetId }, { onSuccess: () => onOpenChange(false) })}
        >
          <Play className="h-4 w-4" /> Start Assessment
        </Button>
      </DialogFooter>
    </>
  );
}

/** Advanced Mode: today's original flow, unchanged -- pick specific scanners/targets/profiles
 * and queue them directly, bypassing the Pipeline Decision Engine entirely. */
function ManualExecuteView({
  assessmentId,
  onOpenChange,
  onBackToPipeline,
}: {
  assessmentId: string;
  onOpenChange: (open: boolean) => void;
  onBackToPipeline: () => void;
}) {
  const { data: tools } = useTools();
  const { data: targetsPage } = useTargets(assessmentId, { page_size: 200, enabled: true });
  const executeMutation = useExecuteAssessment(assessmentId);

  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [selectedTargetIds, setSelectedTargetIds] = useState<string[] | "all">("all");
  const [advancedMode, setAdvancedMode] = useState(false);
  const [profileSelections, setProfileSelections] = useState<Record<string, string>>({});

  const runnableTools = (tools ?? []).filter((tool) => tool.is_installed && tool.enabled);
  const targets = targetsPage?.items ?? [];

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

    // Simplified mode (the default): send no tool_options at all -- every plugin's build_command()
    // already falls back to its own recommended DEFAULT_PROFILE_ID when profile_id is omitted, so
    // "professional defaults first" requires zero extra plumbing here. Advanced Mode only sends an
    // entry for a tool the user actually chose a profile for.
    const toolOptions = advancedMode
      ? Object.fromEntries(
          Object.entries(profileSelections)
            .filter(([toolName]) => selectedTools.includes(toolName))
            .map(([toolName, profileId]) => [toolName, { profile_id: profileId }]),
        )
      : undefined;

    executeMutation.mutate(
      {
        tool_names: selectedTools,
        target_ids: selectedTargetIds === "all" ? null : selectedTargetIds,
        tool_options: toolOptions && Object.keys(toolOptions).length > 0 ? toolOptions : undefined,
      },
      { onSuccess: () => onOpenChange(false) },
    );
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>Run Scanners Individually</DialogTitle>
        <DialogDescription>
          Choose your target(s) and scanner(s) and start — each scanner runs with its recommended, production-safe
          profile automatically. Bypasses the Assessment Pipeline's automatic scanner chaining.
        </DialogDescription>
      </DialogHeader>

      <div className="space-y-5">
        <Button variant="ghost" size="sm" className="px-0 text-muted-foreground" onClick={onBackToPipeline}>
          ← Back to the one-click Start Assessment
        </Button>

        <div>
          <p className="mb-2 text-sm font-medium text-foreground">1. Scanner(s)</p>
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

        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-sm font-medium text-foreground">2. Target(s) ({targets.length} enabled)</p>
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

        <div className="rounded-xl border border-border/60 bg-secondary/15">
          <button
            type="button"
            className="flex w-full items-center gap-2 px-3 py-2 text-sm font-medium text-foreground"
            onClick={() => setAdvancedMode((previous) => !previous)}
          >
            {advancedMode ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            Advanced Scanner Configuration
            <span className="ml-auto text-xs font-normal text-muted-foreground">Optional — choose a specific profile per scanner</span>
          </button>
          {advancedMode && (
            <div className="space-y-4 border-t border-border/50 p-3">
              {selectedTools.length === 0 ? (
                <p className="text-sm text-muted-foreground">Select at least one scanner above first.</p>
              ) : (
                selectedTools.map((toolName) => (
                  <ToolProfileSelector
                    key={toolName}
                    toolName={toolName}
                    profileId={profileSelections[toolName] ?? null}
                    onChange={(profileId) => setProfileSelections((previous) => ({ ...previous, [toolName]: profileId }))}
                  />
                ))
              )}
            </div>
          )}
        </div>
      </div>

      <DialogFooter>
        <Button variant="outline" onClick={() => onOpenChange(false)}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} disabled={selectedTools.length === 0 || targets.length === 0 || executeMutation.isPending}>
          <Play className="h-4 w-4" /> Start Assessment
        </Button>
      </DialogFooter>
    </>
  );
}

/** One tool's profile picker inside Advanced Mode. Renders nothing for a tool with no Scan Profile system. */
function ToolProfileSelector({
  toolName,
  profileId,
  onChange,
}: {
  toolName: string;
  profileId: string | null;
  onChange: (profileId: string) => void;
}) {
  const { data: profiles } = useScanProfiles(toolName);

  // Pre-select the tool's own recommended profile the first time its list loads, so opening
  // Advanced Mode always starts from a sensible choice rather than an empty picker.
  useEffect(() => {
    if (profiles && profiles.length > 0 && profileId === null) {
      const recommended = profiles.find((profile) => KNOWN_RECOMMENDED_PROFILE_IDS.includes(profile.id)) ?? profiles[0];
      onChange(recommended.id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profiles, profileId]);

  if (profiles !== undefined && profiles.length === 0) {
    return null;
  }

  return (
    <div>
      <p className="mb-2 text-sm font-medium capitalize text-foreground">{toolName} profile</p>
      {profiles === undefined ? (
        <p className="text-sm text-muted-foreground">Loading profiles…</p>
      ) : (
        <Select value={profileId ?? undefined} onValueChange={onChange}>
          <SelectTrigger>
            <SelectValue placeholder="Choose a profile…" />
          </SelectTrigger>
          <SelectContent>
            {profiles.map((profile) => (
              <SelectItem key={profile.id} value={profile.id}>
                {profile.name} — {profile.estimated_duration}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
    </div>
  );
}
