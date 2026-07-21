import { Server } from "lucide-react";
import { Link } from "react-router-dom";

import { ChartCard } from "@/components/charts/ChartCard";
import { DistributionBarChart } from "@/components/charts/DistributionBarChart";
import { StatTile } from "@/components/charts/StatTile";
import { TrendAreaChart } from "@/components/charts/TrendAreaChart";
import { EmptyState } from "@/components/common/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useDashboard } from "@/hooks/useDashboard";

export default function HostOverview() {
  const { data: dashboard, isLoading, isError } = useDashboard();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (isError || !dashboard) {
    return <EmptyState title="Couldn't load host overview" description="Something went wrong talking to the backend." icon={<Server className="h-5 w-5" />} />;
  }

  if (dashboard.overview.hosts_discovered === 0) {
    return (
      <EmptyState
        title="No hosts discovered yet"
        description="Run a tool against a target to start populating host inventory statistics here."
        action={<Button asChild><Link to="/tools">Review Tools</Link></Button>}
        icon={<Server className="h-5 w-5" />}
      />
    );
  }

  return (
    <div className="space-y-7">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-primary/80">Host Inventory</p>
        <h1 className="text-4xl font-semibold tracking-normal text-foreground">Host overview</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          Real, deduplicated inventory across every assessment — operating systems, technologies, services, and exposure.
        </p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Hosts" value={dashboard.host_summary.hosts} />
        <StatTile label="Operating systems" value={dashboard.host_summary.operating_systems} />
        <StatTile label="Technologies" value={dashboard.host_summary.technologies} />
        <StatTile label="Services" value={dashboard.host_summary.services} />
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <ChartCard title="Operating systems" isEmpty={dashboard.host_dashboard.operating_systems.length === 0} emptyMessage="No OS candidates detected yet.">
          <DistributionBarChart data={dashboard.host_dashboard.operating_systems} />
        </ChartCard>
        <ChartCard title="Technology distribution" isEmpty={dashboard.host_dashboard.technology_distribution.length === 0} emptyMessage="No technologies detected yet.">
          <DistributionBarChart data={dashboard.host_dashboard.technology_distribution} />
        </ChartCard>
        <ChartCard title="Top open ports" isEmpty={dashboard.host_summary.top_open_ports.length === 0} emptyMessage="No open ports recorded yet.">
          <DistributionBarChart data={dashboard.host_summary.top_open_ports} />
        </ChartCard>
        <ChartCard title="Service distribution" isEmpty={dashboard.host_dashboard.service_distribution.length === 0} emptyMessage="No named services recorded yet.">
          <DistributionBarChart data={dashboard.host_dashboard.service_distribution} />
        </ChartCard>
      </section>

      <ChartCard title="Host growth" description="New hosts discovered per day (last 30 days).">
        <TrendAreaChart data={dashboard.charts.host_growth} colorIndex={0} />
      </ChartCard>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-center justify-between pb-2">
            <CardTitle>Newest hosts</CardTitle>
            <Button asChild variant="ghost" size="sm"><Link to="/hosts">View all</Link></Button>
          </CardHeader>
          <div className="divide-y divide-border/50 px-2 pb-2">
            {dashboard.host_dashboard.newest.map((host) => (
              <Link key={host.id} to={`/hosts/${host.id}`} className="flex items-center justify-between gap-3 rounded-xl px-4 py-3 transition-colors hover:bg-secondary/40">
                <p className="truncate font-medium text-foreground">{host.hostname ?? host.ipv4 ?? host.ipv6}</p>
                <span className="text-xs text-muted-foreground">{new Date(host.first_seen).toLocaleDateString()}</span>
              </Link>
            ))}
          </div>
        </Card>
        <ChartCard title="Most active hosts" description="By number of discovered services." isEmpty={dashboard.host_dashboard.most_active.length === 0}>
          <DistributionBarChart data={dashboard.host_dashboard.most_active} />
        </ChartCard>
      </div>
    </div>
  );
}
