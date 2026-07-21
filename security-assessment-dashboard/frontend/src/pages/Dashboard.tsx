import {
  Activity,
  ClipboardList,
  Cpu,
  Eye,
  FileBarChart,
  Layers,
  Network,
  RefreshCw,
  Server,
  ShieldAlert,
  Target,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { DistributionBarChart } from "@/components/charts/DistributionBarChart";
import { StatTile } from "@/components/charts/StatTile";
import { TrendAreaChart } from "@/components/charts/TrendAreaChart";
import { ChartCard } from "@/components/charts/ChartCard";
import { EmptyState } from "@/components/common/EmptyState";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useAssessments } from "@/hooks/useAssessments";
import { useDashboard } from "@/hooks/useDashboard";
import { useRunCorrelation } from "@/hooks/useFindings";

export default function Dashboard() {
  const [assessmentId, setAssessmentId] = useState<string>("all");
  const scopedId = assessmentId === "all" ? undefined : assessmentId;

  const assessmentsQuery = useAssessments({ sort_by: "created_at", sort_dir: "desc", page: 1, page_size: 100 });
  const dashboardQuery = useDashboard(scopedId);
  const runCorrelation = useRunCorrelation();

  const assessments = assessmentsQuery.data?.items ?? [];
  const dashboard = dashboardQuery.data;

  return (
    <div className="space-y-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-[0.18em] text-primary/80">Intelligence Dashboard</p>
          <h1 className="text-4xl font-semibold tracking-normal text-foreground">Security overview</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Real, collected assessment data — hosts, services, observations, and correlated findings.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Select value={assessmentId} onValueChange={setAssessmentId}>
            <SelectTrigger className="w-56">
              <SelectValue placeholder="All assessments" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All assessments</SelectItem>
              {assessments.map((assessment) => (
                <SelectItem key={assessment.id} value={assessment.id}>
                  {assessment.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" disabled={runCorrelation.isPending} onClick={() => runCorrelation.mutate(scopedId)}>
            <RefreshCw className={`h-4 w-4 ${runCorrelation.isPending ? "animate-spin" : ""}`} />
            Run Correlation
          </Button>
        </div>
      </div>

      {dashboardQuery.isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      )}

      {dashboardQuery.isError && (
        <EmptyState
          title="Couldn't load the dashboard"
          description="Something went wrong talking to the backend."
          icon={<ShieldAlert className="h-5 w-5" />}
        />
      )}

      {!dashboardQuery.isLoading && !dashboardQuery.isError && dashboard && dashboard.is_empty && (
        <EmptyState
          title="No data collected yet"
          description="This workspace has no hosts, observations, or findings yet. Create an assessment, add targets, and run a tool to start populating the dashboard with real collected data."
          action={
            <Button asChild>
              <Link to="/assessments">Go to Assessments</Link>
            </Button>
          }
          secondaryAction={
            <Button asChild variant="outline">
              <Link to="/tools">Review Tools</Link>
            </Button>
          }
          tip="Once a scan completes, click 'Run Correlation' above to generate findings from the collected observations."
          icon={<Activity className="h-5 w-5" />}
        />
      )}

      {!dashboardQuery.isLoading && !dashboardQuery.isError && dashboard && !dashboard.is_empty && (
        <>
          {/* Overview */}
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
            <StatTile label="Assessments" value={dashboard.overview.assessments} icon={<ClipboardList className="h-4.5 w-4.5" />} />
            <StatTile label="Targets" value={dashboard.overview.targets} icon={<Target className="h-4.5 w-4.5" />} />
            <StatTile label="Hosts" value={dashboard.overview.hosts_discovered} icon={<Server className="h-4.5 w-4.5" />} />
            <StatTile label="Services" value={dashboard.overview.services} icon={<Network className="h-4.5 w-4.5" />} />
            <StatTile label="Technologies" value={dashboard.overview.technologies} icon={<Layers className="h-4.5 w-4.5" />} />
            <StatTile label="Observations" value={dashboard.overview.observations} icon={<Eye className="h-4.5 w-4.5" />} />
            <StatTile label="Findings" value={dashboard.overview.findings} icon={<ShieldAlert className="h-4.5 w-4.5" />} />
            <StatTile label="Reports" value={dashboard.overview.reports} icon={<FileBarChart className="h-4.5 w-4.5" />} />
          </section>

          {/* Security summary + execution summary */}
          <section className="grid gap-5 lg:grid-cols-2">
            <ChartCard
              title="Security summary"
              description="Findings by severity across the correlated dataset."
              isEmpty={dashboard.overview.findings === 0}
              emptyMessage="No findings yet. Run the Correlation Engine after a scan completes."
            >
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

            <Card>
              <CardHeader className="pb-2">
                <CardTitle>Execution summary</CardTitle>
                <CardDescription>Tool execution outcomes across every job.</CardDescription>
              </CardHeader>
              <div className="grid grid-cols-2 gap-3 px-6 pb-6 sm:grid-cols-4">
                <StatTile label="Completed" value={dashboard.execution_summary.completed} />
                <StatTile label="Running" value={dashboard.execution_summary.running} />
                <StatTile label="Failed" value={dashboard.execution_summary.failed} />
                <StatTile label="Cancelled" value={dashboard.execution_summary.cancelled} />
                <div className="col-span-2 sm:col-span-4">
                  <StatTile
                    label="Average duration"
                    value={
                      dashboard.execution_summary.average_duration_seconds != null
                        ? `${dashboard.execution_summary.average_duration_seconds.toFixed(1)}s`
                        : "—"
                    }
                    icon={<Cpu className="h-4.5 w-4.5" />}
                  />
                </div>
              </div>
            </Card>
          </section>

          {/* Trend charts */}
          <section className="grid gap-5 lg:grid-cols-2">
            <ChartCard
              title="Finding trend"
              description="New findings recorded per day (last 30 days)."
              isEmpty={dashboard.charts.finding_trend.length === 0}
              emptyMessage="No findings recorded in the last 30 days."
            >
              <TrendAreaChart data={dashboard.charts.finding_trend} colorIndex={7} />
            </ChartCard>
            <ChartCard
              title="Host growth"
              description="New hosts discovered per day (last 30 days)."
              isEmpty={dashboard.charts.host_growth.length === 0}
              emptyMessage="No hosts discovered in the last 30 days."
            >
              <TrendAreaChart data={dashboard.charts.host_growth} colorIndex={0} />
            </ChartCard>
            <ChartCard
              title="Execution timeline"
              description="Tool executions planned per day (last 30 days)."
              isEmpty={dashboard.charts.execution_timeline.length === 0}
              emptyMessage="No executions in the last 30 days."
            >
              <TrendAreaChart data={dashboard.charts.execution_timeline} colorIndex={4} />
            </ChartCard>
            <ChartCard
              title="Observation trend"
              description="New observations recorded per day (last 30 days)."
              isEmpty={dashboard.charts.observation_trend.length === 0}
              emptyMessage="No observations recorded in the last 30 days."
            >
              <TrendAreaChart data={dashboard.charts.observation_trend} colorIndex={2} />
            </ChartCard>
          </section>

          {/* Finding dashboard */}
          <section className="space-y-4">
            <h2 className="text-lg font-semibold text-foreground">Findings</h2>
            <div className="grid gap-5 lg:grid-cols-3">
              <ChartCard
                title="By category"
                isEmpty={dashboard.finding_dashboard.by_category.length === 0}
                emptyMessage="No findings yet."
              >
                <DistributionBarChart data={dashboard.finding_dashboard.by_category} />
              </ChartCard>
              <ChartCard
                title="By plugin"
                isEmpty={dashboard.finding_dashboard.by_plugin.length === 0}
                emptyMessage="No findings yet."
              >
                <DistributionBarChart data={dashboard.finding_dashboard.by_plugin} />
              </ChartCard>
              <ChartCard
                title="By host"
                description="Top hosts by finding count."
                isEmpty={dashboard.finding_dashboard.by_host.length === 0}
                emptyMessage="No findings yet."
              >
                <DistributionBarChart data={dashboard.finding_dashboard.by_host} />
              </ChartCard>
            </div>

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
                {dashboard.finding_dashboard.newest.length === 0 && (
                  <p className="px-4 py-6 text-sm text-muted-foreground">No findings recorded yet.</p>
                )}
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
          </section>

          {/* Host dashboard */}
          <section className="space-y-4">
            <h2 className="text-lg font-semibold text-foreground">Hosts</h2>
            <div className="grid gap-5 lg:grid-cols-2">
              <ChartCard
                title="Operating systems"
                isEmpty={dashboard.host_dashboard.operating_systems.length === 0}
                emptyMessage="No OS candidates detected yet."
              >
                <DistributionBarChart data={dashboard.host_dashboard.operating_systems} />
              </ChartCard>
              <ChartCard
                title="Technology distribution"
                isEmpty={dashboard.host_dashboard.technology_distribution.length === 0}
                emptyMessage="No technologies detected yet."
              >
                <DistributionBarChart data={dashboard.host_dashboard.technology_distribution} />
              </ChartCard>
              <ChartCard
                title="Top open ports"
                isEmpty={dashboard.host_summary.top_open_ports.length === 0}
                emptyMessage="No open ports recorded yet."
              >
                <DistributionBarChart data={dashboard.host_summary.top_open_ports} />
              </ChartCard>
              <ChartCard
                title="Service distribution"
                isEmpty={dashboard.host_dashboard.service_distribution.length === 0}
                emptyMessage="No services recorded yet."
              >
                <DistributionBarChart data={dashboard.host_dashboard.service_distribution} />
              </ChartCard>
            </div>

            <Card>
              <CardHeader className="flex-row items-center justify-between pb-2">
                <CardTitle>Newest hosts</CardTitle>
                <Button asChild variant="ghost" size="sm">
                  <Link to="/hosts">View all</Link>
                </Button>
              </CardHeader>
              <div className="divide-y divide-border/50 px-2 pb-2">
                {dashboard.host_dashboard.newest.length === 0 && (
                  <p className="px-4 py-6 text-sm text-muted-foreground">No hosts discovered yet.</p>
                )}
                {dashboard.host_dashboard.newest.map((host) => (
                  <Link
                    key={host.id}
                    to={`/hosts/${host.id}`}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-xl px-4 py-3 transition-colors hover:bg-secondary/40"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium text-foreground">{host.hostname ?? host.ipv4 ?? host.ipv6}</p>
                      <p className="text-xs text-muted-foreground">{host.service_count} service(s)</p>
                    </div>
                    <span className="text-xs text-muted-foreground">{new Date(host.first_seen).toLocaleDateString()}</span>
                  </Link>
                ))}
              </div>
            </Card>
          </section>
        </>
      )}
    </div>
  );
}
