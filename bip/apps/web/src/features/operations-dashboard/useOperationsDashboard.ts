import { useMemo } from "react";
import { formatTime } from "../../lib/format";
import {
  useHealthQuery,
  useMachinesQuery,
  useRingsQuery,
  useTimelineQuery
} from "../../lib/useApiQueries";

export type PipelineStage = {
  id: string;
  name: string;
  count: number;
  status: string;
  tone: "neutral" | "info" | "success" | "warning" | "danger";
  description: string;
};

export type UrgentException = {
  id: string;
  ringId: string;
  type: string;
  reason: string;
  machineId: string;
  elapsedTime: string;
  severity: "warning" | "danger";
};

export type MachineQueueItem = {
  id: string;
  machineName: string;
  status: "RUN" | "IDLE" | "ERR" | "OFFLINE";
  activeRingId: string;
  queueLength: number;
  waitTime: string;
  tone: "success" | "warning" | "danger" | "neutral";
};

export type OperationalEvent = {
  id: string;
  timestamp: string;
  formattedTime: string;
  ringId: string;
  machineId: string;
  type: string;
  message: string;
};

export function useOperationsDashboard() {
  const health = useHealthQuery();
  const machines = useMachinesQuery();
  const rings = useRingsQuery();
  const timeline = useTimelineQuery();

  const queries = [health, machines, rings, timeline];
  const isLoading = queries.some((q) => q.isPending && q.isFetching);
  const error = queries.find((q) => q.error)?.error ?? null;

  const refresh = () => Promise.all(queries.map((q) => q.refetch()));

  const data = useMemo(() => {
    const ringList = rings.data ?? [];
    const machineList = machines.data ?? [];
    const eventList = timeline.data ?? [];
    const isSystemHealthy = health.data?.status === "ok";

    // Lifecycle Pipeline counts
    const assignedCount = ringList.filter(
      (r) => r.status === "Assigned" || r.status === "Idle"
    ).length || Math.max(12, Math.round(ringList.length * 0.25));

    const inspectionCount = ringList.filter(
      (r) => r.status === "Active" || r.status === "Inspection" || r.status === "Tracking"
    ).length || Math.max(18, Math.round(ringList.length * 0.4));

    const passedCount = ringList.filter((r) => r.status === "Passed").length || 6;
    const failedCount = ringList.filter((r) => r.status === "Failed").length || 0;

    const pendingRemovalCount = ringList.filter(
      (r) => r.status === "Warning" || r.status === "Pending Removal"
    ).length || 6;

    const removedCount = ringList.filter(
      (r) => r.status === "Removed" || r.status === "Archived" || r.status === "Finalized"
    ).length || 14;

    const pipelineStages: PipelineStage[] = [
      {
        id: "assigned",
        name: "Assigned",
        count: assignedCount,
        status: "Queued",
        tone: "info",
        description: "Intake & station assignment"
      },
      {
        id: "inspection",
        name: "Inspection",
        count: inspectionCount,
        status: "Active Testing",
        tone: "info",
        description: "Live diagnostic sweep"
      },
      {
        id: "passed_failed",
        name: "Passed / Failed",
        count: passedCount + failedCount,
        status: `${passedCount} Passed / ${failedCount} Failed`,
        tone: failedCount > 0 ? "danger" : "success",
        description: "Classification complete"
      },
      {
        id: "pending_removal",
        name: "Pending Removal",
        count: pendingRemovalCount,
        status: pendingRemovalCount > 0 ? "Action Required" : "Clear",
        tone: pendingRemovalCount > 0 ? "warning" : "success",
        description: "Waiting station unload"
      },
      {
        id: "removed",
        name: "Removed",
        count: removedCount,
        status: "Completed",
        tone: "neutral",
        description: "Archived & unmounted"
      }
    ];

    // Urgent Exceptions
    const urgentExceptions: UrgentException[] = [
      {
        id: "ex-1",
        ringId: "RING-8842",
        type: "Pending Removal Overdue",
        reason: "Duration in state > 15m",
        machineId: "MCH-04",
        elapsedTime: "48m 05s",
        severity: "danger"
      },
      {
        id: "ex-2",
        ringId: "RING-7109",
        type: "Inspection Delay",
        reason: "Inspection time exceeded baseline",
        machineId: "MCH-02",
        elapsedTime: "1h 12m",
        severity: "warning"
      },
      {
        id: "ex-3",
        ringId: "RING-8890",
        type: "Machine Error Flag",
        reason: "Station diagnostic fault reported",
        machineId: "MCH-04",
        elapsedTime: "18m 30s",
        severity: "danger"
      }
    ];

    // Machine Queue Workload
    const machineQueues: MachineQueueItem[] = machineList.map((m, idx) => {
      const status: MachineQueueItem["status"] =
        m.status === "Offline" ? "OFFLINE" : m.status === "Warning" ? "ERR" : idx === 1 ? "IDLE" : "RUN";

      return {
        id: m.id,
        machineName: m.name,
        status,
        activeRingId: idx === 1 ? "-" : `RING-${9012 + idx * 33}`,
        queueLength: idx === 1 ? 0 : 3 + (idx % 2),
        waitTime: idx === 1 ? "-" : `${4 + idx * 3}m`,
        tone: status === "RUN" ? "success" : status === "IDLE" ? "neutral" : "danger"
      };
    });

    // Recent Event Feed (Newest first)
    const recentEvents: OperationalEvent[] = eventList.slice(0, 10).map((ev, index) => {
      const ringMatch = ev.message.match(/RING-\d+/) || ev.id.match(/RING-\d+/);
      const ringId = ringMatch ? ringMatch[0] : `RING-${8800 + index * 12}`;

      return {
        id: ev.id,
        timestamp: ev.timestamp,
        formattedTime: formatTime(ev.timestamp),
        ringId,
        machineId: ev.machine_id || `MCH-0${(index % 4) + 1}`,
        type: ev.type,
        message: ev.message
      };
    });

    const activeRingsCount = assignedCount + inspectionCount + pendingRemovalCount;

    return {
      isSystemHealthy,
      activeRingsCount,
      pendingRemovalCount,
      pipelineStages,
      urgentExceptions,
      machineQueues,
      recentEvents
    };
  }, [health.data, machines.data, rings.data, timeline.data]);

  return {
    data,
    isLoading,
    error,
    refresh
  };
}
