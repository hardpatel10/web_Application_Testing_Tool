import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { CHART_CHROME, SEVERITY_COLOR, categoricalColor } from "@/utils/chart-palette";

interface DistributionItem {
  label: string;
  count: number;
}

interface DistributionBarChartProps {
  data: DistributionItem[];
  colorMode?: "categorical" | "severity";
  height?: number;
}

/**
 * A single-series horizontal bar chart: one bar per category, identity carried by the
 * Y-axis tick label (no legend needed -- see the dataviz skill's "single series" rule),
 * value direct-labeled at the bar tip.
 */
export function DistributionBarChart({ data, colorMode = "categorical", height }: DistributionBarChartProps) {
  const rows = data.slice(0, 8);
  const chartHeight = height ?? Math.max(rows.length * 36, 120);

  return (
    <ResponsiveContainer width="100%" height={chartHeight}>
      <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 36, bottom: 4, left: 4 }} barCategoryGap={8}>
        <XAxis type="number" hide />
        <YAxis
          type="category"
          dataKey="label"
          width={140}
          tickLine={false}
          axisLine={false}
          tick={{ fill: CHART_CHROME.axis, fontSize: 12 }}
          tickFormatter={(value: string) => (value.length > 20 ? `${value.slice(0, 19)}…` : value)}
        />
        <Tooltip
          cursor={{ fill: "hsl(var(--secondary))", opacity: 0.4 }}
          contentStyle={{ background: CHART_CHROME.tooltipBg, border: `1px solid ${CHART_CHROME.tooltipBorder}`, borderRadius: 12, fontSize: 12 }}
          labelStyle={{ color: CHART_CHROME.text }}
          itemStyle={{ color: CHART_CHROME.text }}
        />
        <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={20}>
          {rows.map((row, index) => (
            <Cell
              key={`${row.label}-${index}`}
              fill={colorMode === "severity" ? SEVERITY_COLOR[row.label.toLowerCase()] ?? categoricalColor(index) : categoricalColor(index)}
            />
          ))}
          <LabelList dataKey="count" position="right" style={{ fill: CHART_CHROME.mutedText, fontSize: 12 }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
