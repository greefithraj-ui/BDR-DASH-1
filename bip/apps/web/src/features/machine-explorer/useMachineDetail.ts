import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { apiClient } from "../../lib/apiClient";
import { formatDateTime } from "../../lib/format";
import { queryKeys } from "../../lib/queryKeys";
import type {
  HealthFactor,
  MachineBatterySummary,
  MachineChartPlaceholder,
  MachineDetail,
  MachineDetailEvent,
  MachineRecord,
  MachineTimelineStage
} from "./machineExplorer.types";

const DATA_STALE_TIME = 30_000;

const TIMELINE_STAGES = ["Commissioned", "Operational", "Maintenance", "Under Review", "Retired"];

function pad(value: number, width = 2): string {
  return String(value).padStart(width, "0");
}

function buildRecentEvents(record: MachineRecord): MachineDetailEvent[] {
  return [
    {
      id: `${record.id}-event-1`,
      event: record.status === "Online" ? "Machine reported nominal" : "Machine went offline",
      context: `${record.machineId} ${record.status.toLowerCase()} · ${record.slotsOccupied}/${record.slotCount} slots occupied`,
      timestamp: record.lastSeen
    },
    {
      id: `${record.id}-event-2`,
      event: "Collector heartbeat received",
      context: `${record.machineId} collector is ${record.status.toLowerCase()}`,
      timestamp: "08:50"
    },
    {
      id: `${record.id}-event-3`,
      event: "Battery inventory refreshed",
      context: `${record.activeBatteries} active · ${record.pendingRemovalCount} pending removal`,
      timestamp: "08:45"
    }
  ];
}

function buildTimeline(record: MachineRecord): MachineTimelineStage[] {
  const reachedCount = record.status === "Offline" ? 3 : 2;

  return TIMELINE_STAGES.map((stage, index) => ({
    id: `stage-${index + 1}`,
    name: stage,
    reached: index < reachedCount,
    current: index === reachedCount - 1,
    note: index < reachedCount ? "Stage reached" : "Stage pending"
  }));
}

function buildCharts(): MachineChartPlaceholder[] {
  return [
    {
      id: "machine-chart-slot-occupancy",
      title: "Slot Occupancy",
      description: "Placeholder chart container for future slot occupancy history."
    },
    {
      id: "machine-chart-health-trend",
      title: "Battery Health Trend",
      description: "Placeholder chart container for future battery health trend data."
    }
  ];
}

function buildHealthFactors(record: MachineRecord): HealthFactor[] {
  const scoreTone: HealthFactor["tone"] = record.healthScore >= 80 ? "success" : record.healthScore >= 60 ? "info" : "danger";

  return [
    { label: "Health Score", value: `${Math.round(record.healthScore)}/100`, tone: scoreTone },
    { label: "Battery Distribution", value: `${record.activeBatteries} active on machine`, tone: "neutral" },
    { label: "Firmware Coverage", value: record.dominantFirmware ? `${record.dominantFirmware} dominant` : "Not reported", tone: "info" },
    { label: "Data Freshness", value: record.status === "Online" ? "Nominal" : "Stale", tone: record.status === "Online" ? "success" : "danger" }
  ];
}

export function useMachineDetail(record: MachineRecord | null) {
  const machineId = record?.machineId ?? "";
  const { data: machine, error, isPending, isFetching, refetch } = useQuery({
    queryKey: queryKeys.machines.detail(machineId),
    queryFn: () => apiClient.getMachine(machineId),
    enabled: machineId.length > 0,
    staleTime: DATA_STALE_TIME
  });

  const detail = useMemo<MachineDetail | null>(() => {
    if (!record) {
      return null;
    }

    const freshRecord: MachineRecord = machine
      ? {
          ...record,
          machineId: machine.name,
          name: machine.name,
          status: machine.status === "Offline" ? "Offline" : "Online",
          healthScore: machine.health_score,
          lastSeen: formatDateTime(machine.last_seen) || record.lastSeen,
          dominantFirmware: machine.firmware || record.dominantFirmware,
          firmwareSummary: machine.firmware ? [{ firmware: machine.firmware, count: 0 }] : []
        }
      : record;

    const slotOverview = Array.from({ length: Math.max(freshRecord.slotCount, 0) }, (_, slotIndex) => {
      const slot = `S${pad(slotIndex + 1)}`;
      const occupied = slotIndex < freshRecord.slotsOccupied;

      if (!occupied) {
        return { slot, occupied: false };
      }

      return { slot, occupied: true, currentState: "Tracking", tone: "info" as const };
    });

    const batteryList: MachineBatterySummary[] = [];

    return {
      record: freshRecord,
      slotOverview,
      batteryList,
      recentEvents: buildRecentEvents(freshRecord),
      timeline: buildTimeline(freshRecord),
      charts: buildCharts(),
      healthFactors: buildHealthFactors(freshRecord)
    };
  }, [record, machine]);

  return {
    detail,
    isLoading: isPending && isFetching,
    error: error ?? null,
    refresh: refetch
  };
}