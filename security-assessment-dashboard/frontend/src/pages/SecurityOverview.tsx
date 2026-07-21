import { ShieldAlert, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { ChartCard } from "@/components/charts/ChartCard";
import { DistributionBarChart } from "@/components/charts/DistributionBarChart";
import { StatTile } from "@/components/charts/StatTile";
import { TrendAreaChart } from "@/components/charts/TrendAreaChart";
import { EmptyState } from "@/components/common/EmptyState";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useDashboard } from "@/hooks/useDashboard";

export default function SecurityOverview() {
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
    return <EmptyState title="Couldn't load security overview" description="Something went wrong talking to the backend." icon={<ShieldAlert className="h-5 w-5" />} />;
  }

  const totalFindings = dashboard.overview.findings;

  return (
    <div className="space-y-7">
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-primary/80">Correlation Engine</p>
        <h1 className="text-4xl font-semibold tracking-normal text-foreground">Security overview</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          Workspace-wide risk posture, derived entirely from correlated findings — no severity is ever assigned without a supporting rule.
        </p>
      </div>

      {totalFindings === 0 ? (
        <EmptyState
          title="No findings yet"
          description="Run a scan and the Correlation Engine to see severity distribution, category breakdown, and risk trends here."
          action={<Button asChild><Link to="/findings">Go to Findings</Link></Button>}
          icon={<ShieldCheck className="h-5 w-5" />}
        />
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
            <StatTile label="Critical" value={dashboard.security_summary.critical} />
            <StatTile label="High" value={dashboard.security_summary.high} />
            <StatTile label="Medium" value={dashboard.security_summary.medium} />
            <StatTile label="Low" value={dashboard.security_summary.low} />
            <StatTile label="Informational" value={dashboard.security_summary.info} />
          </section>

          <section className="grid gap-5 lg:grid-cols-2">
            <ChartCard title="Severity distribution">
              <DistributionBarChart
                colorMode="severity"
                data={[
                  { label: "critical", count: dashboard.security_summary.critical },
                  { label: "high", count: dashboard.security_summary.high },
                  { label: "medium", count: dashboard.security_summary.medium },
                  { label: "low", count: dashboard.security_summary.low },
                  { label: "info", count: dashboard.security_summary.info },
                ]}
                height={200}
              />
            </ChartCard>
            <ChartCard title="Findings by category" isEmpty={dashboard.finding_dashboard.by_category.length === 0}>
              <DistributionBarChart data={dashboard.finding_dashboard.by_category} />
            </ChartCard>
            <ChartCard title="Findings by plugin" isEmpty={dashboard.finding_dashboard.by_plugin.length === 0}>
              <DistributionBarChart data={dashboard.finding_dashboard.by_plugin} />
            </ChartCard>
            <ChartCard title="Most affected hosts" isEmpty={dashboard.finding_dashboard.by_host.length === 0}>
              <DistributionBarChart data={dashboard.finding_dashboard.by_host} />
            </ChartCard>
          </section>

          <ChartCard title="Finding trend" description="New findings recorded per day (last 30 days).">
            <TrendAreaChart data={dashboard.charts.finding_trend} colorIndex={7} />
          </ChartCard>

          <Card>
            <CardHeader className="flex-row items-center justify-between pb-2">
              <div>
                <CardTitle>Newest findings</CardTitle>
                <CardDescription>
                  {dashboard.finding_dashboard.open_count} open · {dashboard.finding_dashboard.resolved_count} resolved
                </CardDescription>
              </div>
              <Button asChild variant="ghost" size="sm">
                <Link to="/findings">View all</Link>
              </Button>
            </CardHeader>
            <div className="divide-y divide-border/50 px-2 pb-2">
              {dashboard.finding_dashboard.newest.map((finding) => (
                <Link
                  key={finding.id}
                  to={`/findings/${finding.id}`}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl px-4 py-3 transition-colors hover:bg-secondary/40"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium text-foreground">{finding.title}</p>
                    <p className="text-xs text-muted-foreground">{finding.host_label ?? "Unscoped"}</p>
                  </div>
                  <SeverityBadge severity={finding.severity} />
                </Link>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
