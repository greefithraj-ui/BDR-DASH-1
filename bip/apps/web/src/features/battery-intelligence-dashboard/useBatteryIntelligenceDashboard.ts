import { useMemo } from "react";
import { formatTime, toDisplayCount } from "../../lib/format";
import {
  useAnalyticsSummaryQuery,
  useHealthQuery,
  useMachinesQuery,
  useMetricsQuery,
  useQualitySummaryQuery,
  useRingsQuery,
  useTimelineQuery
} from "../../lib/useApiQueries";
import type { BatteryIntelligenceDashboardData } from "./batteryIntelligence.types";

const EMPTY_DASHBOARD: BatteryIntelligenceDashboardData = {
  statusMetrics: [],
  machineHealth: [],
  ringStates: [],
  activeMachines: [],
  lifecycle: [],
  collectorStatus: [],
  pendingRemovals: [
    {
      id: "pr-1",
      batteryId: "BAT-1024",
      ring: "Ring 22",
      reason: "Operator flag",
      age: "18 min",
      tone: "warning"
    },
    {
      id: "pr-2",
      batteryId: "BAT-1098",
      ring: "Ring 11",
      reason: "Quality review",
      age: "31 min",
      tone: "danger"
    },
    {
      id: "pr-3",
      batteryId: "BAT-1142",
      ring: "Ring 08",
      reason: "Lifecycle closeout",
      age: "44 min",
      tone: "warning"
    }
  ],
  recentEvents: [],
  systemHealth: [],
  charts: [
    {
      id: "chart-ring-distribution",
      title: "Ring State Distribution",
      description: "Placeholder chart container for future ring state visualization."
    },
    {
      id: "chart-lifecycle",
      title: "Battery Lifecycle Overview",
      description: "Placeholder chart container for future lifecycle visualization."
    },
    {
      id: "chart-machine-health",
      title: "Machine Health Summary",
      description: "Placeholder chart container for future machine health visualization."
    }
  ]
};

export function useBatteryIntelligenceDashboard() {
  const metrics = useMetricsQuery();
  const analytics = useAnalyticsSummaryQuery();
  const quality = useQualitySummaryQuery();
  const machines = useMachinesQuery();
  const rings = useRingsQuery();
  const timeline = useTimelineQuery();
  const health = useHealthQuery();

  const queries = [metrics, analytics, quality, machines, rings, timeline, health];

  const isLoading = queries.some((query) => query.isPending && query.isFetching);
  const error = queries.find((query) => query.error)?.error ?? null;
  const refresh = () => Promise.all(queries.map((query) => query.refetch()));

  const data = useMemo<BatteryIntelligenceDashboardData>(() => {
    const metric = (id: string) => metrics.data?.items.find((item) => item.id === id);
    const analyticsItem = (key: string) => analytics.data?.items.find((item) => item.key === key);
    const qualityItem = (id: string) => quality.data?.items.find((item) => item.id === id);

    const activeRings = metric("MT-1")?.value ?? 0;
    const bdrSlots = metric("MT-3")?.value ?? 0;
    const pendingRemovals = metric("MT-4")?.value ?? 0;
    const finalizedRings = metric("MT-5")?.value ?? 0;
    const eventIntakeReady = metric("MT-6")?.status === "ok";
    const runningSlots = analyticsItem("slots_running")?.value ?? 0;
    const assignedSlots = qualityItem("QL-4")?.value ?? 0;
    const passRate = qualityItem("QL-1")?.value ?? 0;
    const completedSlots = qualityItem("QL-5")?.value ?? 0;
    const failedSlots = qualityItem("QL-2")?.value ?? 0;
    const passedSlots = Math.round((completedSlots * passRate) / 100);
    const machinesList = machines.data ?? [];
    const machinesOnline = machinesList.filter((machine) => machine.status !== "Offline").length;
    const machinesTotal = machinesList.length;
    const onlineRatio = machinesTotal > 0 ? machinesOnline / machinesTotal : 0;

    const machineHealth = [...machinesList]
      .sort((a, b) => a.health_score - b.health_score)
      .slice(0, 3)
      .map((machine, index) => {
        const offline = machine.status === "Offline";
        const warning = machine.status === "Warning";
        return {
          id: `mh-${index + 1}`,
          machine: machine.name,
          status: offline ? "Offline" : warning ? "Watch" : "Online",
          detail: offline ? "Heartbeat lost" : warning ? "Delayed signal" : "Heartbeat received",
          tone: (offline ? "danger" : warning ? "warning" : "success") as BatteryIntelligenceDashboardData["machineHealth"][number]["tone"]
        };
      });

    const ringList = rings.data ?? [];
    const activeRingCount = ringList.filter((ring) => ring.status === "Active").length;
    const warningRingCount = ringList.filter((ring) => ring.status === "Warning").length;

    const activeMachines = machinesList
      .filter((machine) => machine.status !== "Offline")
      .slice(0, 4)
      .map((machine, index) => ({
        id: `am-${index + 1}`,
        name: machine.name,
        currentRing: ["Ring 14", "Ring 22", "Ring 05", "Ring 31"][index] ?? `Ring ${index + 1}`,
        operatorState: ["Tracking", "Pending removal", "Inspecting", "Tracking"][index] ?? "Tracking",
        tone: "success" as const
      }));

    const latestTimestamp = machinesList
      .map((machine) => machine.last_seen)
      .filter((value) => value)
      .sort()
      .at(-1);

    const eventList = timeline.data ?? [];

    return {
      statusMetrics: [
        { id: "active-batteries", label: "Active Batteries", value: toDisplayCount(activeRings), helper: "Live active inventory", tone: "success" },
        { id: "tracking", label: "Tracking", value: toDisplayCount(runningSlots), helper: "Live tracking state", tone: "info" },
        { id: "pending-removal", label: "Pending Removal", value: toDisplayCount(pendingRemovals), helper: "Live removal queue", tone: pendingRemovals > 0 ? "warning" : "success" },
        { id: "finalized", label: "Finalized", value: toDisplayCount(finalizedRings), helper: "Live completed lifecycle", tone: "neutral" },
        { id: "passed", label: "Passed", value: toDisplayCount(passedSlots), helper: "Live pass classification", tone: "success" },
        { id: "failed", label: "Failed", value: toDisplayCount(failedSlots), helper: "Live fail classification", tone: failedSlots > 0 ? "danger" : "success" }
      ],
      machineHealth,
      ringStates: [
        { id: "rs-1", state: "Active", value: toDisplayCount(activeRingCount), tone: "success" },
        { id: "rs-2", state: "Idle", value: "0", tone: "neutral" },
        { id: "rs-3", state: "Review", value: toDisplayCount(warningRingCount), tone: "warning" },
        { id: "rs-4", state: "Exception", value: "0", tone: "danger" }
      ],
      activeMachines,
      lifecycle: [
        { id: "lc-1", stage: "Registered", count: toDisplayCount(bdrSlots), description: "Intake stage" },
        { id: "lc-2", stage: "Tracking", count: toDisplayCount(runningSlots), description: "Active tracking stage" },
        { id: "lc-3", stage: "Review", count: toDisplayCount(assignedSlots), description: "Engineering review stage" },
        { id: "lc-4", stage: "Finalized", count: toDisplayCount(finalizedRings), description: "Closed lifecycle stage" }
      ],
      collectorStatus: [
        { id: "cs-1", label: "Collector Mode", value: health.data?.status === "ok" ? "Online" : "Offline", tone: "success" },
        { id: "cs-2", label: "Last Sync", value: latestTimestamp ? formatTime(latestTimestamp) : "-", tone: "info" },
        { id: "cs-3", label: "Queue", value: "Clear", tone: "success" }
      ],
      pendingRemovals: EMPTY_DASHBOARD.pendingRemovals,
      recentEvents: eventList.map((event, index) => ({
        id: `be-${index + 1}`,
        event: event.type,
        batteryId: event.machine_id || "-",
        context: event.message,
        timestamp: formatTime(event.timestamp)
      })),
      systemHealth: [
        { id: "sh-1", label: "Platform", value: health.data?.status === "ok" ? "Stable" : "Degraded", tone: "success" },
        { id: "sh-2", label: "Event Intake", value: eventIntakeReady ? "Ready" : "Degraded", tone: eventIntakeReady ? "info" : "danger" },
        { id: "sh-3", label: "Operator View", value: "Available", tone: "success" },
        { id: "sh-4", label: "Data Freshness", value: onlineRatio >= 0.9 ? "Nominal" : "Stale", tone: onlineRatio >= 0.9 ? "success" : "warning" }
      ],
      charts: EMPTY_DASHBOARD.charts
    } satisfies BatteryIntelligenceDashboardData;
  }, [metrics.data, analytics.data, quality.data, machines.data, rings.data, timeline.data, health.data]);

  return {
    data,
    error,
    isLoading,
    isEmpty: data.statusMetrics.length === 0,
    refresh
  };
}
