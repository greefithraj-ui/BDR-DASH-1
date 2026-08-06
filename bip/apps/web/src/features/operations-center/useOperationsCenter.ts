import { useEffect, useMemo, useState } from "react";
import { formatTime } from "../../lib/format";
import {
  useHealthQuery,
  useMachinesQuery,
  useRingsQuery,
  useTimelineQuery
} from "../../lib/useApiQueries";

export type StatusTokenKey =
  | "assigned"
  | "inspection"
  | "passed"
  | "pending-removal"
  | "removed"
  | "failed"
  | "offline";

export type PipelineStage = {
  id: string;
  name: string;
  count: number;
  avgDuration: string;
  targetDuration: string;
  variance: string;
  isVarianceAlert: boolean;
  longestWaitingRing: string;
  longestWaitTimer: string;
  statusTokenKey: StatusTokenKey;
  description: string;
};

export type ExceptionItem = {
  id: string;
  ringId: string;
  machineId: string;
  collectorId: string;
  operatorId: string;
  type: string;
  reason: string;
  elapsedSeconds: number;
  severity: "critical" | "warning" | "normal";
  requiredAction: string;
};

export type ProductionBlocker = {
  id: string;
  title: string;
  category: "Machine Offline" | "Collector Offline" | "Ring Waiting Too Long" | "Inspection Timeout";
  affectedEntity: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM";
  impact: string;
  requiredAction: string;
};

export type GroupedExceptions = {
  byMachine: Record<string, ExceptionItem[]>;
  byRing: Record<string, ExceptionItem[]>;
  byCollector: Record<string, ExceptionItem[]>;
  byOperator: Record<string, ExceptionItem[]>;
};

export type MachineQueueItem = {
  id: string;
  machineName: string;
  statusIcon: "🟢" | "🟡" | "🔵" | "🟠" | "🔴" | "⚫";
  statusText: string;
  statusTokenKey: StatusTokenKey;
  currentRing: string;
  currentDurationSeconds: number;
  queueLength: number;
  queuePreview: string[];
  waitTime: string;
  nextExpectedAction: string;
};

export type AgingBucket = {
  label: "0–5 min" | "5–10 min" | "10–20 min" | "20+ min";
  count: number;
  rings: string[];
  isOverdue: boolean;
};

export type OperationalEvent = {
  id: string;
  timestamp: string;
  timeDisplay: string;
  ringId: string;
  machineId: string;
  operatorId: string;
  eventType: string;
  message: string;
};

export type RingFocus = {
  ringId: string;
  serialNumber: string;
  machineId: string;
  currentStateToken: StatusTokenKey;
  stateLabel: string;
  currentDurationSeconds: number;
  requiredAction: string;
};

export type SuggestedAction = {
  actionLabel: string;
  ringId: string;
  statusTokenKey: StatusTokenKey;
};

export function formatTimerHHMMSS(totalSeconds: number): string {
  const hrs = Math.floor(totalSeconds / 3600);
  const mins = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;
  return [hrs, mins, secs].map((v) => String(v).padStart(2, "0")).join(":");
}

export function useOperationsCenter() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedRingId, setSelectedRingId] = useState<string | null>("BAT-1024");
  const [liveSeconds, setLiveSeconds] = useState<number>(1103);
  const [lastRefreshTime, setLastRefreshTime] = useState<string>(
    new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
  );

  // Live Activity Ticker
  useEffect(() => {
    const timer = setInterval(() => {
      setLiveSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Global Keyboard Shortcuts (Ctrl+K or /)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey && e.key === "k") || (e.key === "/" && document.activeElement?.tagName !== "INPUT")) {
        e.preventDefault();
        const searchInput = document.querySelector<HTMLInputElement>(".opsc-search-input");
        if (searchInput) {
          searchInput.focus();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const health = useHealthQuery();
  const machines = useMachinesQuery();
  const rings = useRingsQuery();
  const timeline = useTimelineQuery();

  const queries = [health, machines, rings, timeline];
  const isLoading = queries.some((q) => q.isPending && q.isFetching);
  const error = queries.find((q) => q.error)?.error ?? null;

  const refresh = async () => {
    await Promise.all(queries.map((q) => q.refetch()));
    setLastRefreshTime(
      new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    );
  };

  // Single Shared Operational State
  const operationalState = useMemo(() => {
    const ringList = rings.data ?? [];
    const machineList = machines.data ?? [];
    const eventList = timeline.data ?? [];
    const isSystemHealthy = health.data?.status === "ok";

    // Pipeline counts
    const assignedCount = ringList.filter((r) => r.status === "Assigned" || r.status === "Idle").length || 14;
    const inspectionCount = ringList.filter((r) => r.status === "Active" || r.status === "Inspection" || r.status === "Tracking").length || 22;
    const passedCount = ringList.filter((r) => r.status === "Passed").length || 8;
    const failedCount = ringList.filter((r) => r.status === "Failed").length || 1;
    const pendingRemovalCount = ringList.filter((r) => r.status === "Warning" || r.status === "Pending Removal").length || 5;
    const removedCount = ringList.filter((r) => r.status === "Removed" || r.status === "Archived").length || 18;

    const pipelineStages: PipelineStage[] = [
      {
        id: "assigned",
        name: "Assigned",
        count: assignedCount,
        avgDuration: "00:04:12",
        targetDuration: "< 00:05:00",
        variance: "🟢 OK",
        isVarianceAlert: false,
        longestWaitingRing: "BAT-1042",
        longestWaitTimer: formatTimerHHMMSS(724),
        statusTokenKey: "assigned",
        description: "Intake & station load assignment"
      },
      {
        id: "inspection",
        name: "Inspection",
        count: inspectionCount,
        avgDuration: "00:24:30",
        targetDuration: "< 00:18:00",
        variance: "🟡 +36% Delay",
        isVarianceAlert: true,
        longestWaitingRing: "BAT-1098",
        longestWaitTimer: formatTimerHHMMSS(2530),
        statusTokenKey: "inspection",
        description: "Active diagnostic sweep"
      },
      {
        id: "passed_failed",
        name: "Passed / Failed",
        count: passedCount + failedCount,
        avgDuration: "00:01:15",
        targetDuration: "< 00:03:00",
        variance: "🟢 OK",
        isVarianceAlert: false,
        longestWaitingRing: "BAT-1102",
        longestWaitTimer: formatTimerHHMMSS(315),
        statusTokenKey: failedCount > 0 ? "failed" : "passed",
        description: `${passedCount} Passed / ${failedCount} Failed`
      },
      {
        id: "pending_removal",
        name: "Pending Removal",
        count: pendingRemovalCount,
        avgDuration: "00:18:12",
        targetDuration: "< 00:05:00",
        variance: "🔴 +264% BOTTLENECK",
        isVarianceAlert: true,
        longestWaitingRing: "BAT-1024",
        longestWaitTimer: formatTimerHHMMSS(liveSeconds),
        statusTokenKey: "pending-removal",
        description: "Waiting station unmount & unload"
      },
      {
        id: "removed",
        name: "Removed",
        count: removedCount,
        avgDuration: "00:00:00",
        targetDuration: "N/A",
        variance: "🟢 Complete",
        isVarianceAlert: false,
        longestWaitingRing: "-",
        longestWaitTimer: "-",
        statusTokenKey: "removed",
        description: "Archived & unmounted"
      }
    ];

    // Aging Buckets
    const agingBuckets: AgingBucket[] = [
      {
        label: "0–5 min",
        count: 16,
        rings: ["BAT-1150", "BAT-1152", "BAT-1155"],
        isOverdue: false
      },
      {
        label: "5–10 min",
        count: 9,
        rings: ["BAT-1142", "BAT-1144"],
        isOverdue: false
      },
      {
        label: "10–20 min",
        count: 4,
        rings: ["BAT-1042", "BAT-1088"],
        isOverdue: false
      },
      {
        label: "20+ min",
        count: 3,
        rings: ["BAT-1024", "BAT-1098"],
        isOverdue: true
      }
    ];

    // Production Blockers
    const productionBlockers: ProductionBlocker[] = [
      {
        id: "pb-1",
        title: "Station AQC-04 Unload Overdue",
        category: "Ring Waiting Too Long",
        affectedEntity: "BAT-1024 (AQC-04)",
        severity: "CRITICAL",
        impact: "Blocking 3 queued rings on Station AQC-04",
        requiredAction: "Operator OP-44 must unmount BAT-1024 immediately."
      },
      {
        id: "pb-2",
        title: "Station AQC-01 Safety Lockout",
        category: "Machine Offline",
        affectedEntity: "AQC-01 (Inspection Bay A)",
        severity: "CRITICAL",
        impact: "Station offline for 31 minutes",
        requiredAction: "Shift supervisor must inspect interlock latch & reset station."
      },
      {
        id: "pb-3",
        title: "Collector COL-02 Telemetry Delay",
        category: "Collector Offline",
        affectedEntity: "Collector COL-02",
        severity: "HIGH",
        impact: "Heartbeat ping delayed by 14 minutes",
        requiredAction: "Verify RS-485 bus cable on Collector Bay B."
      },
      {
        id: "pb-4",
        title: "Thermal Stabilization Timeout",
        category: "Inspection Timeout",
        affectedEntity: "BAT-1098 (AQC-02)",
        severity: "MEDIUM",
        impact: "Inspection cycle runtime exceeded target by 36%",
        requiredAction: "Review cell delta voltage stabilization trace."
      }
    ];

    // Urgent Exceptions
    const rawExceptions: ExceptionItem[] = [
      {
        id: "ex-1",
        ringId: "BAT-1024",
        machineId: "AQC-04",
        collectorId: "COL-01",
        operatorId: "OP-44",
        type: "Pending Removal Overdue",
        reason: "Ring waiting for unmount > 45 minutes",
        elapsedSeconds: liveSeconds,
        severity: "critical",
        requiredAction: "IMMEDIATE: Operator OP-44 must unmount BAT-1024 from Station AQC-04."
      },
      {
        id: "ex-4",
        ringId: "BAT-1088",
        machineId: "AQC-01",
        collectorId: "COL-03",
        operatorId: "OP-08",
        type: "Station Emergency Hold",
        reason: "Manual safety hold initiated by operator",
        elapsedSeconds: 1900,
        severity: "critical",
        requiredAction: "INSPECT: Verify physical station interlocks on AQC-01 before reset."
      },
      {
        id: "ex-2",
        ringId: "BAT-1098",
        machineId: "AQC-02",
        collectorId: "COL-02",
        operatorId: "OP-12",
        type: "Inspection Cycle Exceeded",
        reason: "Inspection sweep cycle time exceeding baseline",
        elapsedSeconds: 2530,
        severity: "warning",
        requiredAction: "MONITOR: Review cell thermal stabilization trace on AQC-02."
      },
      {
        id: "ex-3",
        ringId: "BAT-1142",
        machineId: "AQC-04",
        collectorId: "COL-01",
        operatorId: "OP-44",
        type: "Telemetry Ping Delay",
        reason: "Voltage delta anomaly reported by station sensor",
        elapsedSeconds: 1145,
        severity: "warning",
        requiredAction: "CALIBRATE: Re-check collector COL-01 bus connection."
      }
    ];

    // Grouping
    const groupedExceptions: GroupedExceptions = {
      byMachine: {},
      byRing: {},
      byCollector: {},
      byOperator: {}
    };

    for (const item of rawExceptions) {
      if (!groupedExceptions.byMachine[item.machineId]) groupedExceptions.byMachine[item.machineId] = [];
      groupedExceptions.byMachine[item.machineId].push(item);

      if (!groupedExceptions.byRing[item.ringId]) groupedExceptions.byRing[item.ringId] = [];
      groupedExceptions.byRing[item.ringId].push(item);

      if (!groupedExceptions.byCollector[item.collectorId]) groupedExceptions.byCollector[item.collectorId] = [];
      groupedExceptions.byCollector[item.collectorId].push(item);

      if (!groupedExceptions.byOperator[item.operatorId]) groupedExceptions.byOperator[item.operatorId] = [];
      groupedExceptions.byOperator[item.operatorId].push(item);
    }

    // Machine Queue
    const machineQueues: MachineQueueItem[] = machineList.map((m, idx) => {
      let statusIcon: MachineQueueItem["statusIcon"] = "🟢";
      let statusText = "RUNNING";
      let statusTokenKey: StatusTokenKey = "passed";
      let nextExpectedAction = "Complete inspection sweep";
      let queuePreview: string[] = ["BAT-9102", "BAT-9105"];

      if (m.status === "Offline") {
        statusIcon = "⚫";
        statusText = "OFFLINE";
        statusTokenKey = "offline";
        nextExpectedAction = "Clear interlock safety fault & reset";
        queuePreview = [];
      } else if (m.status === "Warning") {
        statusIcon = "🔴";
        statusText = "ERROR";
        statusTokenKey = "failed";
        nextExpectedAction = "Acknowledge diagnostic alert & clear station";
        queuePreview = ["BAT-9140"];
      } else if (idx === 1) {
        statusIcon = "🟡";
        statusText = "IDLE";
        statusTokenKey = "assigned";
        nextExpectedAction = "Load next queued ring BAT-9102";
        queuePreview = ["BAT-9102"];
      } else if (idx === 0) {
        statusIcon = "🟠";
        statusText = "UNLOAD REQ";
        statusTokenKey = "pending-removal";
        nextExpectedAction = "Unload passed ring BAT-1024 immediately";
        queuePreview = ["BAT-9112", "BAT-9115", "BAT-9120"];
      } else if (idx === 2) {
        statusIcon = "🔵";
        statusText = "INSPECTING";
        statusTokenKey = "inspection";
        nextExpectedAction = "Awaiting final voltage stabilization";
        queuePreview = ["BAT-9132", "BAT-9135"];
      }

      return {
        id: m.id,
        machineName: m.name,
        statusIcon,
        statusText,
        statusTokenKey,
        currentRing: idx === 1 ? "-" : `BAT-${1040 + idx * 18}`,
        currentDurationSeconds: idx === 1 ? 0 : 1100 + idx * 420 + (liveSeconds % 60),
        queueLength: idx === 1 ? 0 : queuePreview.length,
        queuePreview,
        waitTime: idx === 1 ? "-" : `00:${6 + idx * 4}:00`,
        nextExpectedAction
      };
    });

    // Recent Events Feed
    const recentEvents: OperationalEvent[] = eventList.slice(0, 10).map((ev, index) => {
      const ringMatch = ev.message.match(/BAT-\d+/) || ev.message.match(/RING-\d+/);
      const ringId = ringMatch ? ringMatch[0] : `BAT-${1040 + index * 6}`;
      const timeDisplay = ev.timestamp ? formatTime(ev.timestamp) : `09:${14 + index}:${index * 4}`;

      return {
        id: ev.id,
        timestamp: ev.timestamp,
        timeDisplay,
        ringId,
        machineId: ev.machine_id || `AQC-0${(index % 4) + 1}`,
        operatorId: `OP-${10 + (index % 5) * 8}`,
        eventType: ev.type || "STATE_TRANSITION",
        message: ev.message
      };
    });

    // Live Status Panel Metrics
    const machinesOnlineCount = machineList.filter((m) => m.status !== "Offline").length || machineList.length;
    const activeRingsCount = assignedCount + inspectionCount + pendingRemovalCount;

    const latestTimestamp = machineList
      .map((m) => m.last_seen)
      .filter((v) => v)
      .sort()
      .at(-1);

    const lastCollectorSync = latestTimestamp ? formatTime(latestTimestamp) : "16:13:20";

    // Exact Suggested Actions for empty focus state
    const suggestedActions: SuggestedAction[] = [
      { actionLabel: "Remove BAT-1024", ringId: "BAT-1024", statusTokenKey: "pending-removal" },
      { actionLabel: "Review BAT-1042", ringId: "BAT-1042", statusTokenKey: "assigned" },
      { actionLabel: "Inspect BAT-1098", ringId: "BAT-1098", statusTokenKey: "inspection" },
      { actionLabel: "Inspect BAT-1032", ringId: "BAT-1088", statusTokenKey: "failed" }
    ];

    // Current Focus Resolution
    let currentFocus: RingFocus | null = null;
    if (selectedRingId) {
      const foundException = rawExceptions.find((e) => e.ringId === selectedRingId);

      currentFocus = {
        ringId: selectedRingId,
        serialNumber: `SN-2026-X${selectedRingId.replace("BAT-", "")}`,
        machineId: foundException ? foundException.machineId : "AQC-04",
        currentStateToken: (foundException
          ? foundException.type.includes("Pending")
            ? "pending-removal"
            : "inspection"
          : "pending-removal") as StatusTokenKey,
        stateLabel: foundException ? foundException.type : "Pending Removal (Overdue >15m)",
        currentDurationSeconds: selectedRingId === "BAT-1024" ? liveSeconds : 2530,
        requiredAction: foundException
          ? foundException.requiredAction
          : "UNLOAD: Operator OP-44 must unmount ring from AQC-04."
      };
    }

    // Filtered search list for inline dropdown
    const allSearchableRings = [
      "BAT-1024",
      "BAT-1042",
      "BAT-1088",
      "BAT-1098",
      "BAT-1102",
      "BAT-1142",
      "BAT-1150"
    ].filter((id) => id.toLowerCase().includes(searchQuery.toLowerCase()));

    return {
      isSystemHealthy,
      activeRingsCount,
      machinesOnlineCount,
      machinesTotalCount: machineList.length || 4,
      pendingRemovalCount,
      lastCollectorSync,
      pipelineStages,
      agingBuckets,
      productionBlockers,
      sortedExceptions: rawExceptions,
      groupedExceptions,
      machineQueues,
      recentEvents,
      currentFocus,
      suggestedActions,
      allSearchableRings
    };
  }, [health.data, machines.data, rings.data, timeline.data, searchQuery, selectedRingId, liveSeconds]);

  return {
    searchQuery,
    setSearchQuery,
    selectedRingId,
    setSelectedRingId,
    lastRefreshTime,
    data: operationalState,
    isLoading,
    error,
    refresh
  };
}
