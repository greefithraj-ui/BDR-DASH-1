import * as echarts from "echarts/core";
import { BarChart, LineChart, PieChart, ScatterChart } from "echarts/charts";
import {
  DatasetComponent,
  GridComponent,
  LegendComponent,
  TitleComponent,
  ToolboxComponent,
  TooltipComponent,
  TransformComponent
} from "echarts/components";
import { LabelLayout, UniversalTransition } from "echarts/features";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  ScatterChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DatasetComponent,
  TransformComponent,
  ToolboxComponent,
  LabelLayout,
  UniversalTransition,
  CanvasRenderer
]);

export type ChartThemeName = "bip-light" | "bip-dark";

const baseTheme = {
  textStyle: {
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif"
  },
  title: {
    textStyle: { fontWeight: 600 as const, fontSize: 14 }
  },
  legend: {
    icon: "roundRect",
    itemWidth: 12,
    itemHeight: 12,
    textStyle: { fontSize: 12 }
  },
  tooltip: {
    confine: true
  },
  categoryAxis: {
    axisLine: { lineStyle: { width: 1 } },
    axisTick: { alignWithLabel: true },
    splitLine: { show: false }
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false }
  }
};

export const chartThemes: Record<ChartThemeName, Record<string, unknown>> = {
  "bip-light": {
    ...baseTheme,
    color: ["#0891b2", "#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed", "#14b8a6", "#f59e0b"],
    backgroundColor: "transparent",
    textStyle: { color: "#687386", ...baseTheme.textStyle },
    title: { textStyle: { color: "#172033", ...baseTheme.title.textStyle } },
    legend: { textStyle: { color: "#566174", ...baseTheme.legend.textStyle } },
    tooltip: {
      backgroundColor: "#ffffff",
      borderColor: "#d9dee7",
      textStyle: { color: "#172033" },
      ...baseTheme.tooltip
    },
    categoryAxis: {
      ...baseTheme.categoryAxis,
      axisLine: { lineStyle: { color: "#d9dee7" } },
      axisTick: { lineStyle: { color: "#d9dee7" } },
      axisLabel: { color: "#687386" }
    },
    valueAxis: {
      ...baseTheme.valueAxis,
      axisLabel: { color: "#687386" },
      splitLine: { lineStyle: { color: "rgb(18 53 91 / 8%)" } }
    }
  },
  "bip-dark": {
    ...baseTheme,
    color: ["#22d3ee", "#60a5fa", "#34d399", "#fbbf24", "#f87171", "#a78bfa", "#2dd4bf", "#fcd34d"],
    backgroundColor: "transparent",
    textStyle: { color: "#c3cad6", ...baseTheme.textStyle },
    title: { textStyle: { color: "#e9edf5", ...baseTheme.title.textStyle } },
    legend: { textStyle: { color: "#c3cad6", ...baseTheme.legend.textStyle } },
    tooltip: {
      backgroundColor: "#202630",
      borderColor: "#3f4a5d",
      textStyle: { color: "#e9edf5" },
      ...baseTheme.tooltip
    },
    categoryAxis: {
      ...baseTheme.categoryAxis,
      axisLine: { lineStyle: { color: "#3f4a5d" } },
      axisTick: { lineStyle: { color: "#3f4a5d" } },
      axisLabel: { color: "#c3cad6" }
    },
    valueAxis: {
      ...baseTheme.valueAxis,
      axisLabel: { color: "#c3cad6" },
      splitLine: { lineStyle: { color: "rgb(255 255 255 / 8%)" } }
    }
  }
};

let themesRegistered = false;

export function registerChartThemes(): void {
  if (themesRegistered) {
    return;
  }

  echarts.registerTheme("bip-light", chartThemes["bip-light"]);
  echarts.registerTheme("bip-dark", chartThemes["bip-dark"]);
  themesRegistered = true;
}
