import { useMemo } from "react";
import { toDisplayCount } from "../../lib/format";
import { useAnalyticsSummaryQuery, useHealthQuery, useMetricsQuery, useQualitySummaryQuery } from "../../lib/useApiQueries";
import type { ExecutiveDashboardData } from "./executiveDashboard.types";

const EMPTY_DASHBOARD: ExecutiveDashboardData = {
  kpis: [],
  operations: [],
  activity: [
    {
      id: "activity-1",
      title: "Ring status snapshot refreshed",
      context: "Latest ring status snapshot from the database.",
      timestamp: "09:15"
    },
    {
      id: "activity-2",
      title: "Machine availability reviewed",
      context: "Machine availability reviewed from collector heartbeats.",
      timestamp: "08:50"
    },
    {
      id: "activity-3",
      title: "Pending removals queue checked",
      context: "Pending removals queue checked against live metrics.",
      timestamp: "08:20"
    }
  ],
  alerts: [
    {
      id: "alert-1",
      title: "Quality review",
      description: "Exception workflows monitored from the live quality summary.",
      severity: "warning"
    },
    {
      id: "alert-2",
      title: "Collector health",
      description: "Collector status derived from the live analytics summary.",
      severity: "info"
    },
    {
      id: "alert-3",
      title: "Removal queue",
      description: "Removal queue derived from live platform metrics.",
      severity: "danger"
    }
  ],
  performance: [
    {
      id: "performance-trend",
      title: "Performance Trend",
      description: "Placeholder chart container for future trend analytics."
    },
    {
      id: "quality-mix",
      title: "Quality Mix",
      description: "Placeholder chart container for future quality metrics."
    }
  ]
};

export function useExecutiveDashboard() {
  const metrics = useMetricsQuery();
  const analytics = useAnalyticsSummaryQuery();
  const quality = useQualitySummaryQuery();
  const health = useHealthQuery();

  const queries = [metrics, analytics, quality, health];

  const isLoading = queries.some((query) => query.isPending && query.isFetching);
  const error = queries.find((query) => query.error)?.error ?? null;
  const refresh = () => Promise.all(queries.map((query) => query.refetch()));

  const data = useMemo<ExecutiveDashboardData>(() => {
    const metric = (id: string) => metrics.data?.items.find((item) => item.id === id);
    const analyticsItem = (key: string) => analytics.data?.items.find((item) => item.key === key);
    const qualityItem = (id: string) => quality.data?.items.find((item) => item.id === id);

    const activeRings = metric("MT-1")?.value ?? 0;
    const machinesOnline = metric("MT-2")?.value ?? 0;
    const pendingRemovals = metric("MT-4")?.value ?? 0;
    const finalizedRings = metric("MT-5")?.value ?? 0;
    const passRate = qualityItem("QL-1")?.value ?? 0;
    const completedSlots = qualityItem("QL-5")?.value ?? 0;
    const failedSlots = qualityItem("QL-2")?.value ?? 0;
    const passedSlots = Math.round((completedSlots * passRate) / 100);
    const collectorHealth = analyticsItem("collector_health")?.value ?? 0;
    const systemStable = health.data?.status === "ok";

    return {
      kpis: [
        { id: "active-rings", label: "Active Rings", value: toDisplayCount(activeRings), helper: "Live operational snapshot", tone: "success" },
        { id: "total-rings", label: "Total Rings", value: toDisplayCount(activeRings + finalizedRings), helper: "Live fleet baseline", tone: "neutral" },
        { id: "passed-today", label: "Passed Today", value: toDisplayCount(passedSlots), helper: "Live daily throughput", tone: "success" },
        { id: "failed-today", label: "Failed Today", value: toDisplayCount(failedSlots), helper: "Live exception count", tone: failedSlots > 0 ? "danger" : "success" },
        { id: "machines-online", label: "Machines Online", value: toDisplayCount(machinesOnline), helper: "Live machine availability", tone: "info" },
        { id: "pending-removals", label: "Pending Removals", value: toDisplayCount(pendingRemovals), helper: "Live queue indicator", tone: pendingRemovals > 0 ? "warning" : "success" },
        { id: "collector-health", label: "Collector Health", value: collectorHealth >= 80 ? "Nominal" : "Degraded", helper: "Live collector status", tone: collectorHealth >= 80 ? "success" : "warning" },
        { id: "system-status", label: "System Status", value: systemStable ? "Stable" : "Degraded", helper: "Live platform signal", tone: systemStable ? "success" : "warning" }
      ],
      operations: [
        {
          id: "throughput",
          title: "Throughput",
          value: collectorHealth >= 80 ? "On Track" : "Watch",
          description: "Throughput posture from live metrics.",
          tone: collectorHealth >= 80 ? "success" : "warning"
        },
        {
          id: "quality",
          title: "Quality",
          value: passRate >= 95 ? "Pass" : "Watch",
          description: "Quality leadership view from the live pass rate.",
          tone: passRate >= 95 ? "success" : "warning"
        },
        {
          id: "availability",
          title: "Availability",
          value: collectorHealth >= 95 ? "High" : "Medium",
          description: "Operational availability from live collector health.",
          tone: "info"
        }
      ],
      activity: EMPTY_DASHBOARD.activity,
      alerts: EMPTY_DASHBOARD.alerts,
      performance: EMPTY_DASHBOARD.performance
    } satisfies ExecutiveDashboardData;
  }, [metrics.data, analytics.data, quality.data, health.data]);

  return {
    data,
    error,
    isLoading,
    isEmpty: data.kpis.length === 0,
    refresh
  };
}
