import { useMemo } from "react";
import { toDisplayCount } from "../../lib/format";
import {
  useAnalyticsSummaryQuery,
  useMachinesQuery,
  useMetricsQuery,
  usePerformanceSummaryQuery,
  useQualitySummaryQuery,
  useRingsQuery
} from "../../lib/useApiQueries";
import type { AnalyticsCard, AnalyticsTone } from "./analyticsHub.types";

const STATIC_INSIGHTS = [
  {
    id: "insight-1",
    title: "AQC-03 health improved",
    detail: "Health score rose 9 points after firmware update.",
    tag: "Machine",
    tagTone: "info" as const,
    timestamp: "Today 09:40"
  },
  {
    id: "insight-2",
    title: "LFP-280 pass rate rising",
    detail: "QC pass rate climbed to 96.2% this period.",
    tag: "Quality",
    tagTone: "success" as const,
    timestamp: "Today 08:15"
  },
  {
    id: "insight-3",
    title: "Offline events trending down",
    detail: "Machine offline events down 25% over the last 7 days.",
    tag: "Reliability",
    tagTone: "success" as const,
    timestamp: "Yesterday"
  },
  {
    id: "insight-4",
    title: "Firmware v3.0.2 adoption growing",
    detail: "Adoption now covers 54% of the fleet.",
    tag: "Firmware",
    tagTone: "info" as const,
    timestamp: "Yesterday"
  }
];

const STATIC_ALERTS = [
  {
    id: "alert-1",
    severity: "danger" as const,
    title: "3 batteries flagged for exception review",
    detail: "Exception state detected on AQC-02 and AQC-05.",
    timestamp: "Today 09:12"
  },
  {
    id: "alert-2",
    severity: "warning" as const,
    title: "Pending removal backlog",
    detail: "AQC-07 has 4 batteries awaiting removal.",
    timestamp: "Today 08:02"
  },
  {
    id: "alert-3",
    severity: "warning" as const,
    title: "Firmware v1.9.0 below adoption target",
    detail: "Older firmware still on 12% of batteries.",
    timestamp: "Yesterday"
  },
  {
    id: "alert-4",
    severity: "info" as const,
    title: "Slot occupancy at 76%",
    detail: "Fleet-wide occupancy continues to climb.",
    timestamp: "Yesterday"
  }
];

const STATIC_QUICK_NAV = [
  { id: "nav-executive", label: "Executive Dashboard", route: "/executive", description: "Platform overview" },
  { id: "nav-intelligence", label: "Battery Intelligence", route: "/intelligence", description: "AI dashboard" },
  { id: "nav-battery", label: "Battery Explorer", route: "/battery-explorer", description: "Search batteries" },
  { id: "nav-machine", label: "Machine Explorer", route: "/machine-explorer", description: "Inspect machines" },
  { id: "nav-timeline", label: "Timeline", route: "/timeline", description: "Event history" }
];

const STATIC_CHARTS = [
  {
    id: "analytics-chart-health",
    title: "Fleet Health Trend",
    description: "Placeholder chart container for future fleet health history."
  },
  {
    id: "analytics-chart-alerts",
    title: "Alert Volume by Category",
    description: "Placeholder chart container for future alert distribution."
  }
];

function card(
  id: string,
  category: AnalyticsCard["category"],
  title: string,
  description: string,
  status: string,
  statusTone: AnalyticsTone,
  route: string,
  metrics: AnalyticsCard["metrics"]
): AnalyticsCard {
  return {
    id,
    category,
    title,
    description,
    status,
    statusTone,
    route,
    metrics,
    primaryAction: { label: "Open" },
    secondaryAction: { label: "View Charts" }
  };
}

export function useAnalyticsHub() {
  const metrics = useMetricsQuery();
  const analytics = useAnalyticsSummaryQuery();
  const quality = useQualitySummaryQuery();
  const performance = usePerformanceSummaryQuery();
  const machines = useMachinesQuery();
  const rings = useRingsQuery();

  const queries = [metrics, analytics, quality, performance, machines, rings];

  const isLoading = queries.some((query) => query.isPending && query.isFetching);
  const error = queries.find((query) => query.error)?.error ?? null;
  const refresh = () => Promise.all(queries.map((query) => query.refetch()));

  const data = useMemo(() => {
    const metric = (id: string) => metrics.data?.items.find((item) => item.id === id);
    const analyticsItem = (key: string) => analytics.data?.items.find((item) => item.key === key);
    const qualityItem = (id: string) => quality.data?.items.find((item) => item.id === id);
    const performanceItem = (id: string) => performance.data?.items.find((item) => item.id === id);

    const activeRings = metric("MT-1")?.value ?? 0;
    const machinesOnline = metric("MT-2")?.value ?? 0;
    const runningSlots = analyticsItem("slots_running")?.value ?? 0;
    const passRate = qualityItem("QL-1")?.value ?? 0;
    const failedSlots = qualityItem("QL-2")?.value ?? 0;
    const collectorHealth = analyticsItem("collector_health")?.value ?? 0;
    const utilization = performanceItem("PF-2")?.value ?? 0;
    const machinesList = machines.data ?? [];
    const healthScores = machinesList.map((machine) => machine.health_score);
    const averageHealth = healthScores.length > 0 ? Math.round(healthScores.reduce((sum, score) => sum + score, 0) / healthScores.length) : 0;
    const offlineCount = machinesList.length - machinesOnline;
    const ringsCount = rings.data?.length ?? 0;

    return {
      kpis: [
        { id: "kpi-batteries", label: "Batteries Tracked", value: toDisplayCount(activeRings), delta: "+42 this month", deltaTone: "success" as const },
        { id: "kpi-machines", label: "Active Machines", value: toDisplayCount(machinesOnline), delta: "All reporting", deltaTone: "info" as const },
        { id: "kpi-alerts", label: "Open Alerts", value: toDisplayCount(failedSlots), delta: "3 critical", deltaTone: "danger" as const },
        { id: "kpi-health", label: "Fleet Health Score", value: String(averageHealth), delta: "+2 pts vs last month", deltaTone: "success" as const }
      ],
      cards: [
        card("card-machine", "machine", "Machine Analytics Summary", "Machine health, slot occupancy, and battery loads across the fleet.", offlineCount > 0 ? "Watch" : "Nominal", offlineCount > 0 ? "warning" : "success", "/machine-explorer", [
          { label: "Active Machines", value: String(machinesOnline) },
          { label: "Avg Health", value: `${averageHealth}/100` },
          { label: "Slots Used", value: `${utilization}%` },
          { label: "Offline", value: String(offlineCount), tone: offlineCount > 0 ? "warning" : undefined }
        ]),
        card("card-product", "product", "Product Analytics Summary", "Product mix, volume, and distribution across rings.", "On Track", "success", "/production", [
          { label: "Products", value: "5" },
          { label: "LFP-280 Share", value: "38%" },
          { label: "New This Month", value: "120" },
          { label: "Rings in Use", value: toDisplayCount(ringsCount) }
        ]),
        card("card-quality", "quality", "Quality Summary", "QC pass/fail trends and exception counts.", passRate >= 95 ? "Nominal" : "Watch", passRate >= 95 ? "success" : "warning", "/quality", [
          { label: "Pass Rate", value: `${passRate}%`, tone: passRate >= 95 ? "success" : "warning" },
          { label: "Failed", value: toDisplayCount(failedSlots), tone: failedSlots > 0 ? "warning" : undefined },
          { label: "Exceptions", value: "5", tone: "danger" },
          { label: "Reviews Open", value: "4" }
        ]),
        card("card-reliability", "reliability", "Reliability Summary", "Uptime, heartbeat, and offline event trends.", "Nominal", "success", "/reliability", [
          { label: "Uptime", value: "99.4%", tone: "success" },
          { label: "Offline Events", value: String(offlineCount) },
          { label: "Mean Recovery", value: "4.2h" },
          { label: "Collector Health", value: collectorHealth >= 80 ? "Nominal" : "Degraded", tone: collectorHealth >= 80 ? "success" : "warning" }
        ]),
        card("card-performance", "performance", "Performance Summary", "Throughput, cycle performance, and energy metrics.", "Nominal", "success", "/performance", [
          { label: "Throughput", value: toDisplayCount(runningSlots) },
          { label: "Avg Cycle", value: "2.1h" },
          { label: "Energy", value: "98%", tone: "info" },
          { label: "Capacity Use", value: `${utilization}%` }
        ]),
        card("card-trend", "trend", "Trend Summary", "Period-over-period movement of key signals.", "Rising", "info", "/trends", [
          { label: "Batteries", value: "+3.4%", tone: "success" },
          { label: "Alerts", value: "-1.2%", tone: "success" },
          { label: "Health", value: "+2 pts", tone: "success" },
          { label: "Fail Rate", value: "-0.4%", tone: "success" }
        ]),
        card("card-comparison", "comparison", "Comparison Summary", "Fleet and ring comparisons across cohorts.", "Stable", "neutral", "/comparison", [
          { label: "Rings", value: toDisplayCount(ringsCount) },
          { label: "Top Ring", value: "Ring 14" },
          { label: "Spread", value: "8%" },
          { label: "Cohorts", value: "5" }
        ])
      ],
      insights: STATIC_INSIGHTS,
      alerts: STATIC_ALERTS,
      quickNav: STATIC_QUICK_NAV,
      charts: STATIC_CHARTS
    };
  }, [metrics.data, analytics.data, quality.data, performance.data, machines.data, rings.data]);

  return {
    kpis: data.kpis,
    cards: data.cards,
    insights: data.insights,
    alerts: data.alerts,
    quickNav: data.quickNav,
    charts: data.charts,
    isLoading,
    error,
    refresh,
    isEmpty: data.kpis.length === 0
  };
}
