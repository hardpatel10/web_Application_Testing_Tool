import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { CHART_CHROME, categoricalColor } from "@/utils/chart-palette";

interface TrendPoint {
  date: string;
  count: number;
}

interface TrendAreaChartProps {
  data: TrendPoint[];
  colorIndex?: number;
  height?: number;
}

/** A single-series trend line over time -- one hue, a light wash fill, no legend (see the dataviz skill). */
export function TrendAreaChart({ data, colorIndex = 0, height = 220 }: TrendAreaChartProps) {
  const color = categoricalColor(colorIndex);
  const formatDate = (value: unknown) => {
    const date = new Date(String(value));
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={CHART_CHROME.grid} strokeDasharray="0" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={formatDate}
          tickLine={false}
          axisLine={false}
          tick={{ fill: CHART_CHROME.axis, fontSize: 11 }}
          minTickGap={24}
        />
        <YAxis tickLine={false} axisLine={false} tick={{ fill: CHART_CHROME.axis, fontSize: 11 }} allowDecimals={false} width={40} />
        <Tooltip
          labelFormatter={formatDate}
          contentStyle={{ background: CHART_CHROME.tooltipBg, border: `1px solid ${CHART_CHROME.tooltipBorder}`, borderRadius: 12, fontSize: 12 }}
          labelStyle={{ color: CHART_CHROME.text }}
          itemStyle={{ color: CHART_CHROME.text }}
        />
        <defs>
          <linearGradient id={`trend-fill-${colorIndex}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.28} />
            <stop offset="100%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="count"
          stroke={color}
          strokeWidth={2}
          fill={`url(#trend-fill-${colorIndex})`}
          dot={{ r: 4, fill: color, stroke: CHART_CHROME.tooltipBg, strokeWidth: 2 }}
          activeDot={{ r: 5, fill: color, stroke: CHART_CHROME.tooltipBg, strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
