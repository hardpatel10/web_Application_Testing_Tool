import { Layers } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { ChartCard } from "@/components/charts/ChartCard";
import { DistributionBarChart } from "@/components/charts/DistributionBarChart";
import { StatTile } from "@/components/charts/StatTile";
import { EmptyState } from "@/components/common/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useTechnologies } from "@/hooks/useHostInventory";
import { useDashboard } from "@/hooks/useDashboard";

export default function TechnologyOverview() {
  const navigate = useNavigate();
  const { data: dashboard, isLoading, isError } = useDashboard();
  const { data: recentTechnologies } = useTechnologies({ sort_by: "last_seen", sort_dir: "desc", page: 1, page_size: 15 });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (isError || !dashboard) {
    return <EmptyState title="Couldn't load technology overview" description="Something went wrong talking to the backend." icon={<Layers className="h-5 w-5" />} />;
  }

  if (dashboard.host_summary.technologies === 0) {
    return (
      <EmptyState
        title="No technologies detected yet"
        description="Technology signatures are extracted from service banners as scans run. Run a tool with version detection to populate this page."
        action={<Button asChild><Link to="/tools">Review Tools</Link></Button>}
        icon={<Layers className="h-5 w-5" />}
      />
    );
  }

  return (
    <div className="space-y-7">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-primary/80">Host Inventory</p>
        <h1 className="text-4xl font-semibold tracking-normal text-foreground">Technology overview</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          Every distinct product/version signature extracted from collected service data across the workspace.
        </p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2">
        <StatTile label="Distinct technologies" value={dashboard.host_summary.technologies} icon={<Layers className="h-4.5 w-4.5" />} />
        <StatTile label="Hosts with a detected stack" value={dashboard.host_summary.hosts} />
      </section>

      <ChartCard title="Top technologies" isEmpty={dashboard.host_summary.top_technologies.length === 0}>
        <DistributionBarChart data={dashboard.host_summary.top_technologies} />
      </ChartCard>

      <Card>
        <CardHeader className="flex-row items-center justify-between pb-2">
          <CardTitle>Recently seen technologies</CardTitle>
          <Button asChild variant="ghost" size="sm"><Link to="/technologies">View all</Link></Button>
        </CardHeader>
        <div className="divide-y divide-border/50 px-2 pb-2">
          {(recentTechnologies?.items ?? []).length === 0 && (
            <p className="px-4 py-6 text-sm text-muted-foreground">No technologies recorded yet.</p>
          )}
          {(recentTechnologies?.items ?? []).map((technology) => (
            <div
              key={technology.id}
              className="flex cursor-pointer flex-wrap items-center justify-between gap-3 rounded-xl px-4 py-3 transition-colors hover:bg-secondary/40"
              onClick={() => navigate(`/hosts/${technology.host_id}`)}
            >
              <div className="min-w-0">
                <p className="truncate font-medium text-foreground">
                  {technology.name} {technology.version && <span className="text-muted-foreground">{technology.version}</span>}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant="outline" className="capitalize">{technology.category.replace("_", " ")}</Badge>
                <span className="text-xs text-muted-foreground">{new Date(technology.last_seen).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
