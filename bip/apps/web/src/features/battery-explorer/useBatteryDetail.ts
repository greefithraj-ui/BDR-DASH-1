import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { apiClient } from "../../lib/apiClient";
import { formatDateTime } from "../../lib/format";
import { queryKeys } from "../../lib/queryKeys";
import type {
  BatteryDetail,
  BatteryDetailEvent,
  BatteryRecord,
  ChartPlaceholderItem,
  DecisionSummary,
  LifecycleStageDetail
} from "./batteryExplorer.types";

const DATA_STALE_TIME = 30_000;

const TIMELINE_STAGES = ["Registered", "Tracking", "Review", "Finalized"];

const STATE_TIMELINE_INDEX: Record<string, number> = {
  Registered: 1,
  Tracking: 2,
  Idle: 2,
  Review: 3,
  "Pending Removal": 3,
  Exception: 3,
  Finalized: 4
};

const STATE_RECOMMENDATION: Record<string, string> = {
  Registered: "Register on first ring",
  Tracking: "Continue tracking",
  Review: "Route to engineering review",
  "Pending Removal": "Schedule removal and closeout",
  Exception: "Escalate to engineering",
  Finalized: "Archive final record",
  Idle: "No action required"
};

const STATE_FROM_RING_STATUS: Record<string, string> = {
  Active: "Tracking",
  Warning: "Exception",
  Finalized: "Finalized"
};

const LIFECYCLE_BY_STATE: Record<string, string> = {
  Tracking: "In Progress",
  Exception: "Exception",
  Finalized: "Completed"
};

const TONE_BY_STATE: Record<string, BatteryRecord["tone"]> = {
  Tracking: "info",
  Exception: "danger",
  Finalized: "success"
};

function buildLifecycle(record: BatteryRecord): LifecycleStageDetail[] {
  const reachedCount = STATE_TIMELINE_INDEX[record.currentState] ?? 1;

  return TIMELINE_STAGES.map((stage, index) => ({
    id: `stage-${index + 1}`,
    name: stage,
    reached: index < reachedCount,
    current: index === reachedCount - 1 && record.currentState !== "Finalized",
    note: index < reachedCount ? "Stage reached" : "Stage pending"
  }));
}

function buildRecentEvents(record: BatteryRecord): BatteryDetailEvent[] {
  return [
    {
      id: `${record.id}-event-1`,
      event: "Battery observed on ring",
      context: `${record.ringName} · ${record.machine} ${record.slot}`,
      timestamp: record.lastSeen
    },
    {
      id: `${record.id}-event-2`,
      event: "Ring state changed",
      context: `${record.ringName} reported ${record.currentState.toLowerCase()}`,
      timestamp: "08:50"
    },
    {
      id: `${record.id}-event-3`,
      event: "Collector heartbeat received",
      context: `${record.machine} collector is nominal`,
      timestamp: "08:45"
    }
  ];
}

function buildDecisionSummary(record: BatteryRecord): DecisionSummary {
  return {
    recommendation: STATE_RECOMMENDATION[record.currentState] ?? "Continue tracking",
    confidence: "Estimated · 87%",
    note: "Derived from the latest ring snapshot on the collector."
  };
}

function buildCharts(): ChartPlaceholderItem[] {
  return [
    {
      id: "detail-chart-signal-timeline",
      title: "Signal Timeline",
      description: "Placeholder chart container for future signal history."
    },
    {
      id: "detail-chart-state-history",
      title: "State History",
      description: "Placeholder chart container for future state transitions."
    }
  ];
}

export function useBatteryDetail(record: BatteryRecord | null) {
  const ringId = record?.serialNumber ?? "";
  const { data: ring, error, isPending, isFetching, refetch } = useQuery({
    queryKey: queryKeys.rings.detail(ringId),
    queryFn: () => apiClient.getRing(ringId),
    enabled: ringId.length > 0,
    staleTime: DATA_STALE_TIME
  });

  const detail = useMemo<BatteryDetail | null>(() => {
    if (!record) {
      return null;
    }

    const freshRecord: BatteryRecord = ring
      ? (() => {
          const currentState = STATE_FROM_RING_STATUS[ring.status] ?? record.currentState;
          const seen = formatDateTime(ring.installed_at);
          return {
            ...record,
            serialNumber: ring.id,
            ringMac: ring.id,
            ringName: ring.name,
            currentState,
            firstSeen: seen || record.firstSeen,
            lastSeen: seen || record.lastSeen,
            lifecycleStatus: LIFECYCLE_BY_STATE[currentState] ?? record.lifecycleStatus,
            tone: TONE_BY_STATE[currentState] ?? record.tone
          };
        })()
      : record;

    return {
      record: freshRecord,
      lifecycle: buildLifecycle(freshRecord),
      recentEvents: buildRecentEvents(freshRecord),
      decisionSummary: buildDecisionSummary(freshRecord),
      charts: buildCharts()
    };
  }, [record, ring]);

  return {
    detail,
    isLoading: isPending && isFetching,
    error: error ?? null,
    refresh: refetch
  };
}