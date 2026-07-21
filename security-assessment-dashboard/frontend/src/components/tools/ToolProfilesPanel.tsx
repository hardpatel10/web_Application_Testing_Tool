import { ChevronDown, ChevronUp, Copy, MoreHorizontal, Upload } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EmptyState } from "@/components/common/EmptyState";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  useDuplicateScanProfile,
  useExportScanProfile,
  useImportScanProfile,
  useScanProfiles,
  useSetScanProfileEnabled,
} from "@/hooks/useScanProfiles";
import type { ScanProfile } from "@/types/scan-profile";
import type { ToolDetail } from "@/types/tool";

const RISK_VARIANT: Record<ScanProfile["risk_level"], BadgeProps["variant"]> = {
  low: "success",
  medium: "warning",
  high: "destructive",
};

export function ToolProfilesPanel({ tool }: { tool: ToolDetail }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string>("all");
  const [riskLevel, setRiskLevel] = useState<string>("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [duplicateTarget, setDuplicateTarget] = useState<ScanProfile | null>(null);
  const [importOpen, setImportOpen] = useState(false);

  const { data: profiles, isLoading } = useScanProfiles(tool.name, {
    query: query || undefined,
    category: category === "all" ? undefined : category,
    risk_level: riskLevel === "all" ? undefined : riskLevel,
  });
  const setEnabled = useSetScanProfileEnabled(tool.name);
  const exportProfile = useExportScanProfile(tool.name);
  const duplicateProfile = useDuplicateScanProfile(tool.name);
  const importProfile = useImportScanProfile(tool.name);

  if (!tool.supports_profiles) {
    return (
      <EmptyState
        title="No Scan Profiles for this tool"
        description={`${tool.display_name} doesn't have a Scan Profile system -- it runs with its configured default arguments instead.`}
      />
    );
  }

  const categories = Array.from(new Set((profiles ?? []).map((p) => p.category))).sort();

  const handleExport = async (profile: ScanProfile) => {
    const result = await exportProfile.mutateAsync(profile.id);
    await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    toast.success(`'${profile.name}' copied to clipboard as JSON.`);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search profiles…" className="max-w-xs" />
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {categories.map((cat) => (
              <SelectItem key={cat} value={cat}>
                {cat}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={riskLevel} onValueChange={setRiskLevel}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Risk" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All risk levels</SelectItem>
            <SelectItem value="low">Low</SelectItem>
            <SelectItem value="medium">Medium</SelectItem>
            <SelectItem value="high">High</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" className="ml-auto" onClick={() => setImportOpen(true)}>
          <Upload className="h-4 w-4" /> Import
        </Button>
      </div>

      {isLoading && (
        <div className="space-y-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      )}

      {!isLoading && profiles && profiles.length === 0 && (
        <EmptyState title="No profiles match your filters" description="Try a different search or clear your filters." />
      )}

      {!isLoading && profiles && profiles.length > 0 && (
        <div className="space-y-2">
          {profiles.map((profile) => (
            <div key={profile.id} className="rounded-xl border border-border/60 bg-secondary/25 p-4">
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  className="flex flex-1 items-center gap-2 text-left"
                  onClick={() => setExpandedId(expandedId === profile.id ? null : profile.id)}
                >
                  {expandedId === profile.id ? (
                    <ChevronUp className="h-4 w-4 shrink-0 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-foreground">{profile.name}</p>
                    <p className="text-xs text-muted-foreground">{profile.description}</p>
                  </div>
                </button>
                <Badge variant="outline">{profile.category}</Badge>
                <Badge variant={RISK_VARIANT[profile.risk_level]}>{profile.risk_level}</Badge>
                {profile.built_in && <Badge variant="secondary">Built-in</Badge>}
                <span className="text-xs text-muted-foreground">{profile.estimated_duration}</span>
                <div className="flex items-center gap-2">
                  <Switch
                    checked={profile.enabled}
                    onCheckedChange={(checked) => setEnabled.mutate({ profileId: profile.id, enabled: checked })}
                    aria-label={profile.enabled ? "Disable profile" : "Enable profile"}
                  />
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" aria-label="Profile actions">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => setDuplicateTarget(profile)}>Duplicate</DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleExport(profile)}>
                        <Copy className="h-4 w-4" /> Export (copy JSON)
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>

              {expandedId === profile.id && (
                <div className="mt-3 grid grid-cols-1 gap-2 border-t border-border/50 pt-3 text-xs sm:grid-cols-2">
                  <DetailRow label="Arguments" value={profile.arguments.join(" ") || "None"} />
                  <DetailRow label="Supported targets" value={profile.supported_targets.join(", ") || "None"} />
                  {/* Nmap-specific */}
                  {(profile.required_ports || profile.required_scripts.length > 0) && (
                    <>
                      <DetailRow label="Required ports" value={profile.required_ports ?? "Any"} />
                      <DetailRow label="Required scripts" value={profile.required_scripts.join(", ") || "None"} />
                    </>
                  )}
                  {/* Nikto-specific */}
                  {(profile.tuning || profile.plugins.length > 0 || profile.timeout_seconds) && (
                    <>
                      <DetailRow label="Tuning" value={profile.tuning ?? "Default"} />
                      <DetailRow label="Plugins" value={profile.plugins.join(", ") || "All"} />
                      {profile.timeout_seconds && <DetailRow label="Timeout" value={`${profile.timeout_seconds}s`} />}
                    </>
                  )}
                  {/* Nuclei-specific */}
                  {(profile.templates.length > 0 || profile.tags.length > 0 || profile.severities.length > 0) && (
                    <>
                      <DetailRow label="Templates" value={profile.templates.join(", ") || "None"} />
                      {profile.tags.length > 0 && <DetailRow label="Tags" value={profile.tags.join(", ")} />}
                      {profile.exclude_tags.length > 0 && <DetailRow label="Exclude tags" value={profile.exclude_tags.join(", ")} />}
                      {profile.severities.length > 0 && <DetailRow label="Severity filter" value={profile.severities.join(", ")} />}
                    </>
                  )}
                  {profile.minimum_tool_version && (
                    <DetailRow label="Minimum tool version" value={profile.minimum_tool_version} />
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <DuplicateProfileDialog
        profile={duplicateTarget}
        onOpenChange={(open) => !open && setDuplicateTarget(null)}
        onConfirm={(newId, newName) => {
          if (!duplicateTarget) return;
          duplicateProfile.mutate(
            { profileId: duplicateTarget.id, payload: { new_id: newId, new_name: newName || undefined } },
            { onSuccess: () => setDuplicateTarget(null) },
          );
        }}
        isPending={duplicateProfile.isPending}
      />

      <ImportProfileDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        onConfirm={(json) => {
          try {
            const profile = JSON.parse(json) as Record<string, unknown>;
            importProfile.mutate({ profile }, { onSuccess: () => setImportOpen(false) });
          } catch {
            toast.error("That doesn't look like valid JSON.");
          }
        }}
        isPending={importProfile.isPending}
      />
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="font-medium uppercase tracking-wide text-muted-foreground">{label}: </span>
      <span className="break-all font-mono text-foreground">{value}</span>
    </div>
  );
}

function DuplicateProfileDialog({
  profile,
  onOpenChange,
  onConfirm,
  isPending,
}: {
  profile: ScanProfile | null;
  onOpenChange: (open: boolean) => void;
  onConfirm: (newId: string, newName: string) => void;
  isPending: boolean;
}) {
  const [newId, setNewId] = useState("");
  const [newName, setNewName] = useState("");

  return (
    <Dialog
      open={Boolean(profile)}
      onOpenChange={(open) => {
        if (!open) {
          setNewId("");
          setNewName("");
        }
        onOpenChange(open);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Duplicate '{profile?.name}'</DialogTitle>
          <DialogDescription>Creates a new, editable custom profile with the same settings.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground">New profile ID</label>
            <Input value={newId} onChange={(e) => setNewId(e.target.value)} placeholder={`${profile?.id}_copy`} />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">New name (optional)</label>
            <Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder={profile?.name} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={!newId || isPending} onClick={() => onConfirm(newId, newName)}>
            Duplicate
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ImportProfileDialog({
  open,
  onOpenChange,
  onConfirm,
  isPending,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (json: string) => void;
  isPending: boolean;
}) {
  const [json, setJson] = useState("");

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setJson("");
        onOpenChange(next);
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Import Scan Profile</DialogTitle>
          <DialogDescription>Paste a previously exported profile's JSON.</DialogDescription>
        </DialogHeader>
        <Textarea value={json} onChange={(e) => setJson(e.target.value)} rows={10} className="font-mono text-xs" placeholder="{ ... }" />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={!json.trim() || isPending} onClick={() => onConfirm(json)}>
            Import
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
