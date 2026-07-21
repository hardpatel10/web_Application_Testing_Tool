import { Copy, Download, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useJobLogs } from "@/hooks/useExecutions";

interface LogViewerProps {
  jobId: string;
  /** Keep polling for new lines -- pass false once the job has reached a terminal status. */
  isActive: boolean;
}

export function LogViewer({ jobId, isActive }: LogViewerProps) {
  const [search, setSearch] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  const { data, isLoading } = useJobLogs(jobId, search ? { search } : undefined, { poll: isActive });
  const lines = useMemo(() => data?.lines ?? [], [data]);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [lines, autoScroll]);

  function handleScroll() {
    const el = containerRef.current;
    if (!el) return;
    setAutoScroll(el.scrollHeight - el.scrollTop - el.clientHeight < 24);
  }

  async function handleCopy() {
    await navigator.clipboard.writeText(lines.join("\n"));
    toast.success("Logs copied to clipboard.");
  }

  function handleDownload() {
    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `job-${jobId}.log`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search logs…" className="pl-9" />
        </div>
        <Button variant="outline" size="sm" onClick={handleCopy} disabled={lines.length === 0}>
          <Copy className="h-4 w-4" /> Copy
        </Button>
        <Button variant="outline" size="sm" onClick={handleDownload} disabled={lines.length === 0}>
          <Download className="h-4 w-4" /> Download
        </Button>
      </div>
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="h-72 overflow-y-auto rounded-xl border border-border/60 bg-black/40 p-3 font-mono text-xs leading-5 text-foreground/90"
      >
        {isLoading && <p className="text-muted-foreground">Loading…</p>}
        {!isLoading && lines.length === 0 && <p className="text-muted-foreground">No log output yet.</p>}
        {lines.map((line, index) => (
          <div key={index} className="whitespace-pre-wrap break-all">
            {line}
          </div>
        ))}
      </div>
    </div>
  );
}
