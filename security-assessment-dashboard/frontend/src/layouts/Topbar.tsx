import { Command, Search, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Breadcrumbs } from "./Breadcrumbs";

export function Topbar() {
  const navigate = useNavigate();

  return (
    <header className="relative z-10 px-5 pt-5 md:px-8 lg:px-10">
      <div className="mx-auto flex h-14 w-full max-w-7xl items-center justify-between gap-4 rounded-2xl border border-border/70 bg-card/65 px-3 shadow-[0_18px_80px_-48px_rgba(0,0,0,0.95)] backdrop-blur-xl">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-border/70 bg-secondary/60 md:hidden">
            <ShieldCheck className="h-4 w-4 text-primary" />
          </div>
          <Breadcrumbs />
        </div>

        <button
          type="button"
          onClick={() => navigate("/search")}
          className="hidden h-9 min-w-[280px] items-center justify-between gap-3 rounded-xl border border-border/70 bg-secondary/45 px-3 text-sm text-muted-foreground transition-all hover:border-border hover:bg-secondary/70 lg:flex"
          aria-label="Search workspace"
        >
          <span className="flex items-center gap-2">
            <Search className="h-4 w-4" />
            Search workspace
          </span>
          <span className="flex items-center gap-1 rounded-md border border-border/70 bg-background/40 px-1.5 py-0.5 text-[0.68rem]">
            <Command className="h-3 w-3" /> K
          </span>
        </button>
      </div>
    </header>
  );
}
