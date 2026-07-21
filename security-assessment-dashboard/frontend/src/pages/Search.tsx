import { Search as SearchIcon } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { EmptyState } from "@/components/common/EmptyState";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useHostSearch } from "@/hooks/useHostInventory";

const SECTIONS: { key: "hosts" | "services" | "technologies" | "observations" | "findings"; label: string }[] = [
  { key: "findings", label: "Findings" },
  { key: "hosts", label: "Hosts" },
  { key: "services", label: "Services" },
  { key: "technologies", label: "Technologies" },
  { key: "observations", label: "Observations" },
];

export default function Search() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const { data, isLoading } = useHostSearch(query);

  const totalResults = data
    ? data.hosts.length + data.services.length + data.technologies.length + data.observations.length + data.findings.length
    : 0;

  return (
    <div className="space-y-7">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-primary/80">Workspace</p>
        <h1 className="text-4xl font-semibold tracking-normal text-foreground">Search</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          Search across findings, hostname, IP, service, technology, and observation in one place.
        </p>
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/70 p-3 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
        <div className="relative">
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search findings, hostname, IP, service, technology, or observation..."
            className="pl-9"
          />
        </div>
      </div>

      {query.trim().length === 0 && (
        <EmptyState title="Start typing to search" description="Results appear across every finding, host, service, technology, and observation in the inventory." icon={<SearchIcon className="h-5 w-5" />} />
      )}

      {query.trim().length > 0 && isLoading && (
        <div className="space-y-3 rounded-2xl border border-border/70 bg-card/60 p-4">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      )}

      {query.trim().length > 0 && !isLoading && data && totalResults === 0 && (
        <EmptyState title="No results" description={`Nothing matched "${query}".`} icon={<SearchIcon className="h-5 w-5" />} />
      )}

      {query.trim().length > 0 && !isLoading && data && totalResults > 0 && (
        <div className="space-y-6">
          {SECTIONS.map(({ key, label }) => {
            const results = data[key];
            if (results.length === 0) return null;
            return (
              <div key={key} className="rounded-2xl border border-border/70 bg-card/70 p-4 shadow-[0_18px_80px_-55px_rgba(0,0,0,0.95)] backdrop-blur-xl">
                <p className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
                <div className="space-y-1">
                  {results.map((result) => {
                    const target = key === "findings" ? `/findings/${result.id}` : result.host_id ? `/hosts/${result.host_id}` : null;
                    return (
                      <button
                        key={result.id}
                        type="button"
                        onClick={() => target && navigate(target)}
                        disabled={!target}
                        className="flex w-full items-center justify-between rounded-lg border border-transparent px-3 py-2 text-left text-sm transition-colors hover:border-border/60 hover:bg-secondary/40 disabled:cursor-default disabled:opacity-70"
                      >
                        <span className="font-medium text-foreground">{result.label}</span>
                        {result.detail && <span className="capitalize text-muted-foreground">{result.detail}</span>}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
