import { FolderOpen, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { FilesystemBrowseDialog } from "@/components/tools/FilesystemBrowseDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useUpdateToolConfiguration } from "@/hooks/useTools";
import type { ToolDetail } from "@/types/tool";

interface ToolConfigurationFormProps {
  tool: ToolDetail;
}

type BrowseTarget =
  | { kind: "field"; field: "working_directory" | "custom_executable_path" | "output_directory" | "temp_directory" }
  | { kind: "wordlist"; index: number };

export function ToolConfigurationForm({ tool }: ToolConfigurationFormProps) {
  const config = tool.configuration;
  const [enabled, setEnabled] = useState(tool.enabled);
  const [timeout, setTimeout_] = useState(config.timeout?.toString() ?? "");
  const [workingDirectory, setWorkingDirectory] = useState(config.working_directory ?? "");
  const [customExecutablePath, setCustomExecutablePath] = useState(config.custom_executable_path ?? "");
  const [httpProxy, setHttpProxy] = useState(config.http_proxy ?? "");
  const [httpsProxy, setHttpsProxy] = useState(config.https_proxy ?? "");
  const [socksProxy, setSocksProxy] = useState(config.socks_proxy ?? "");
  const [rateLimit, setRateLimit] = useState(config.rate_limit?.toString() ?? "");
  const [retries, setRetries] = useState(config.retries?.toString() ?? "");
  const [outputDirectory, setOutputDirectory] = useState(config.output_directory ?? "");
  const [tempDirectory, setTempDirectory] = useState(config.temp_directory ?? "");
  const [args, setArgs] = useState(config.arguments.join("\n"));
  const [envVars, setEnvVars] = useState<{ key: string; value: string }[]>(
    Object.entries(config.environment_variables).map(([key, value]) => ({ key, value })),
  );
  const [wordlists, setWordlists] = useState<{ slot: string; path: string }[]>(
    Object.entries(config.wordlists).map(([slot, path]) => ({ slot, path })),
  );
  const [browseTarget, setBrowseTarget] = useState<BrowseTarget | null>(null);

  const mutation = useUpdateToolConfiguration(tool.name);

  function handleBrowseSelect(path: string) {
    if (!browseTarget) return;
    if (browseTarget.kind === "field") {
      const setters = {
        working_directory: setWorkingDirectory,
        custom_executable_path: setCustomExecutablePath,
        output_directory: setOutputDirectory,
        temp_directory: setTempDirectory,
      };
      setters[browseTarget.field](path);
    } else {
      setWordlists((rows) => rows.map((row, index) => (index === browseTarget.index ? { ...row, path } : row)));
    }
    setBrowseTarget(null);
  }

  function handleSave() {
    mutation.mutate({
      enabled,
      timeout: timeout ? Number(timeout) : null,
      working_directory: workingDirectory || null,
      custom_executable_path: customExecutablePath || null,
      http_proxy: httpProxy || null,
      https_proxy: httpsProxy || null,
      socks_proxy: socksProxy || null,
      rate_limit: rateLimit ? Number(rateLimit) : null,
      retries: retries ? Number(retries) : null,
      output_directory: outputDirectory || null,
      temp_directory: tempDirectory || null,
      arguments: args
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean),
      environment_variables: Object.fromEntries(envVars.filter((row) => row.key.trim()).map((row) => [row.key, row.value])),
      wordlists: Object.fromEntries(wordlists.filter((row) => row.slot.trim() && row.path.trim()).map((row) => [row.slot, row.path])),
    });
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between rounded-xl border border-border/60 bg-secondary/25 p-4">
        <div>
          <p className="text-sm font-medium text-foreground">Enabled</p>
          <p className="text-xs text-muted-foreground">Disabling a tool marks it "Disabled" and excludes it from future runs.</p>
        </div>
        <Switch checked={enabled} onCheckedChange={setEnabled} />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Default timeout (seconds)">
          <Input type="number" min={1} value={timeout} onChange={(e) => setTimeout_(e.target.value)} placeholder="300" />
        </Field>
        <Field label="Rate limit">
          <Input type="number" min={1} value={rateLimit} onChange={(e) => setRateLimit(e.target.value)} placeholder="No limit" />
        </Field>
        <Field label="Retries">
          <Input type="number" min={0} value={retries} onChange={(e) => setRetries(e.target.value)} placeholder="0" />
        </Field>
        <BrowseField
          label="Working directory"
          value={workingDirectory}
          onChange={setWorkingDirectory}
          onBrowse={() => setBrowseTarget({ kind: "field", field: "working_directory" })}
        />
        <BrowseField
          label="Custom executable path"
          value={customExecutablePath}
          onChange={setCustomExecutablePath}
          onBrowse={() => setBrowseTarget({ kind: "field", field: "custom_executable_path" })}
        />
        <BrowseField
          label="Output directory"
          value={outputDirectory}
          onChange={setOutputDirectory}
          onBrowse={() => setBrowseTarget({ kind: "field", field: "output_directory" })}
        />
        <BrowseField
          label="Temporary directory"
          value={tempDirectory}
          onChange={setTempDirectory}
          onBrowse={() => setBrowseTarget({ kind: "field", field: "temp_directory" })}
        />
        <Field label="HTTP proxy">
          <Input value={httpProxy} onChange={(e) => setHttpProxy(e.target.value)} placeholder="http://127.0.0.1:8080" />
        </Field>
        <Field label="HTTPS proxy">
          <Input value={httpsProxy} onChange={(e) => setHttpsProxy(e.target.value)} placeholder="http://127.0.0.1:8080" />
        </Field>
        <Field label="SOCKS proxy">
          <Input value={socksProxy} onChange={(e) => setSocksProxy(e.target.value)} placeholder="socks5://127.0.0.1:1080" />
        </Field>
      </div>

      <Field label="Extra arguments (one per line)">
        <textarea
          value={args}
          onChange={(e) => setArgs(e.target.value)}
          rows={3}
          className="w-full rounded-xl border border-input/80 bg-secondary/50 px-3 py-2 text-sm text-foreground focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-ring/25"
        />
      </Field>

      <RowEditor
        title="Environment variables"
        rows={envVars}
        keyPlaceholder="VAR_NAME"
        valuePlaceholder="value"
        onChange={setEnvVars}
      />

      <div className="space-y-2">
        <p className="text-sm font-medium text-foreground">Wordlists</p>
        <p className="text-xs text-muted-foreground">Slot name (e.g. "directory", "subdomains") mapped to a file path.</p>
        {wordlists.map((row, index) => (
          <div key={index} className="flex gap-2">
            <Input
              value={row.slot}
              onChange={(e) =>
                setWordlists((rows) => rows.map((r, i) => (i === index ? { ...r, slot: e.target.value } : r)))
              }
              placeholder="directory"
              className="w-40"
            />
            <Input
              value={row.path}
              onChange={(e) =>
                setWordlists((rows) => rows.map((r, i) => (i === index ? { ...r, path: e.target.value } : r)))
              }
              placeholder="/path/to/wordlist.txt"
            />
            <Button type="button" variant="outline" size="icon" onClick={() => setBrowseTarget({ kind: "wordlist", index })}>
              <FolderOpen className="h-4 w-4" />
            </Button>
            <Button type="button" variant="ghost" size="icon" onClick={() => setWordlists((rows) => rows.filter((_, i) => i !== index))}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ))}
        <Button type="button" variant="outline" size="sm" onClick={() => setWordlists((rows) => [...rows, { slot: "", path: "" }])}>
          <Plus className="h-4 w-4" /> Add wordlist
        </Button>
      </div>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Save Configuration"}
        </Button>
      </div>

      {browseTarget && (
        <FilesystemBrowseDialog
          open
          onOpenChange={(open) => !open && setBrowseTarget(null)}
          title={browseTarget.kind === "wordlist" ? "Select wordlist file" : "Select path"}
          selectDirectories={browseTarget.kind === "field" && browseTarget.field !== "custom_executable_path"}
          onSelect={handleBrowseSelect}
        />
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function BrowseField({
  label,
  value,
  onChange,
  onBrowse,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  onBrowse: () => void;
}) {
  return (
    <Field label={label}>
      <div className="flex gap-2">
        <Input value={value} onChange={(e) => onChange(e.target.value)} placeholder="Not set" />
        <Button type="button" variant="outline" size="icon" onClick={onBrowse}>
          <FolderOpen className="h-4 w-4" />
        </Button>
      </div>
    </Field>
  );
}

function RowEditor({
  title,
  rows,
  keyPlaceholder,
  valuePlaceholder,
  onChange,
}: {
  title: string;
  rows: { key: string; value: string }[];
  keyPlaceholder: string;
  valuePlaceholder: string;
  onChange: (rows: { key: string; value: string }[]) => void;
}) {
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-foreground">{title}</p>
      {rows.map((row, index) => (
        <div key={index} className="flex gap-2">
          <Input
            value={row.key}
            onChange={(e) => onChange(rows.map((r, i) => (i === index ? { ...r, key: e.target.value } : r)))}
            placeholder={keyPlaceholder}
            className="w-48"
          />
          <Input
            value={row.value}
            onChange={(e) => onChange(rows.map((r, i) => (i === index ? { ...r, value: e.target.value } : r)))}
            placeholder={valuePlaceholder}
          />
          <Button type="button" variant="ghost" size="icon" onClick={() => onChange(rows.filter((_, i) => i !== index))}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ))}
      <Button type="button" variant="outline" size="sm" onClick={() => onChange([...rows, { key: "", value: "" }])}>
        <Plus className="h-4 w-4" /> Add
      </Button>
    </div>
  );
}
