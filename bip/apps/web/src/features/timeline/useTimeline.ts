import { useMemo, useState } from "react";
import { formatDateTime } from "../../lib/format";
import { useTimelineQuery } from "../../lib/useApiQueries";
import type {
  TimelineEvent,
  TimelineEventType,
  TimelineFilters,
  TimelineGroup,
  TimelineGroupBy,
  TimelineOptions,
  TimelineSort,
  TimelineTone
} from "./timeline.types";

export const TIMELINE_PAGE_SIZE = 5;

export const emptyTimelineFilters: TimelineFilters = {
  search: "",
  machine: "",
  battery: "",
  eventType: "",
  dateFrom: "",
  dateTo: ""
};

const TONE_BY_TYPE: Record<string, TimelineTone> = {
  Observed: "neutral",
  Tracking: "info",
  "Pending Removal": "warning",
  Finalized: "success",
  Passed: "success",
  Failed: "danger",
  Replacement: "info",
  "Machine Offline": "danger",
  "Machine Online": "success",
  "Firmware Changed": "info"
};

function toTimelineEventType(value: string): TimelineEventType {
  return Object.prototype.hasOwnProperty.call(TONE_BY_TYPE, value)
    ? (value as TimelineEventType)
    : "Observed";
}

function matchesFilters(event: TimelineEvent, filters: TimelineFilters): boolean {
  const search = filters.search.trim().toLowerCase();

  if (
    search &&
    !event.type.toLowerCase().includes(search) &&
    !event.batterySerialNumber.toLowerCase().includes(search) &&
    !event.machineId.toLowerCase().includes(search) &&
    !event.slot.toLowerCase().includes(search) &&
    !event.reason.toLowerCase().includes(search)
  ) {
    return false;
  }

  if (filters.machine && event.machineId !== filters.machine) {
    return false;
  }

  if (filters.battery && event.batterySerialNumber !== filters.battery) {
    return false;
  }

  if (filters.eventType && event.type !== filters.eventType) {
    return false;
  }

  if (filters.dateFrom && event.date < filters.dateFrom) {
    return false;
  }

  if (filters.dateTo && event.date > filters.dateTo) {
    return false;
  }

  return true;
}

function deriveOptions(events: TimelineEvent[]): TimelineOptions {
  const unique = <T extends string>(values: T[]): T[] => [...new Set(values)].sort();

  return {
    machines: unique(events.map((event) => event.machineId)),
    batteries: unique(events.map((event) => event.batterySerialNumber)),
    eventTypes: unique(events.map((event) => event.type))
  };
}

function groupKeyFor(event: TimelineEvent, groupBy: TimelineGroupBy): string {
  switch (groupBy) {
    case "machine":
      return event.machineId;
    case "battery":
      return event.batterySerialNumber;
    default:
      return event.date;
  }
}

function groupEvents(events: TimelineEvent[], groupBy: TimelineGroupBy, sort: TimelineSort): TimelineGroup[] {
  const grouped = new Map<string, TimelineEvent[]>();

  for (const event of events) {
    const key = groupKeyFor(event, groupBy);
    const list = grouped.get(key);
    if (list) {
      list.push(event);
    } else {
      grouped.set(key, [event]);
    }
  }

  const groups = [...grouped.entries()].map(([key, groupEventsList]) => ({ key, label: key, events: groupEventsList }));

  groups.sort((a, b) => (sort.direction === "desc" ? b.key.localeCompare(a.key) : a.key.localeCompare(b.key)));

  return groups;
}

function countActiveFilters(filters: TimelineFilters): number {
  return Object.values(filters).filter((value) => value.trim().length > 0).length;
}

function severityForTone(tone: TimelineTone): string {
  switch (tone) {
    case "danger":
      return "High";
    case "warning":
      return "Medium";
    default:
      return "Info";
  }
}

export function useTimeline() {
  const { data, error, isPending, isFetching, refetch } = useTimelineQuery();

  const allEvents = useMemo<TimelineEvent[]>(
    () =>
      (data ?? []).map((event) => {
        const type = toTimelineEventType(event.type);
        const tone = TONE_BY_TYPE[event.type] ?? "neutral";
        const timestamp = formatDateTime(event.timestamp);

        return {
          id: event.id,
          timestamp,
          date: timestamp.slice(0, 10),
          type,
          batterySerialNumber: "",
          machineId: event.machine_id,
          slot: "",
          reason: event.message,
          tone,
          metadata: [
            { label: "Ring", value: "-" },
            { label: "Collector", value: event.machine_id ? `${event.machine_id} collector` : "-" },
            { label: "Severity", value: severityForTone(tone) },
            { label: "Source", value: "Live event" }
          ]
        };
      }),
    [data]
  );

  const [filters, setFilters] = useState<TimelineFilters>(emptyTimelineFilters);
  const [sort, setSort] = useState<TimelineSort>({ direction: "desc" });
  const [groupBy, setGroupBy] = useState<TimelineGroupBy>("date");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<TimelineEvent | null>(null);

  const options = useMemo(() => deriveOptions(allEvents), [allEvents]);

  const filteredEvents = useMemo(() => {
    const filtered = allEvents.filter((event) => matchesFilters(event, filters));
    return filtered.slice().sort((a, b) =>
      sort.direction === "desc" ? b.timestamp.localeCompare(a.timestamp) : a.timestamp.localeCompare(b.timestamp)
    );
  }, [allEvents, filters, sort]);

  const groups = useMemo(() => groupEvents(filteredEvents, groupBy, sort), [filteredEvents, groupBy, sort]);

  const groupCount = groups.length;
  const pageCount = Math.max(1, Math.ceil(groupCount / TIMELINE_PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const pageGroups = groups.slice((safePage - 1) * TIMELINE_PAGE_SIZE, safePage * TIMELINE_PAGE_SIZE);

  const activeFilterCount = countActiveFilters(filters);

  const updateFilters = (patch: Partial<TimelineFilters>) => {
    setFilters((current) => ({ ...current, ...patch }));
    setPage(1);
  };

  const clearFilters = () => {
    setFilters(emptyTimelineFilters);
    setPage(1);
  };

  const toggleSort = () => {
    setSort((current) => ({ direction: current.direction === "desc" ? "asc" : "desc" }));
  };

  const changeGroupBy = (nextGroupBy: TimelineGroupBy) => {
    setGroupBy(nextGroupBy);
    setPage(1);
  };

  const changePage = (nextPage: number) => {
    setPage(Math.max(1, Math.min(nextPage, pageCount)));
  };

  const openDetail = (event: TimelineEvent) => setSelected(event);
  const closeDetail = () => setSelected(null);

  return {
    allEvents,
    options,
    filters,
    updateFilters,
    clearFilters,
    activeFilterCount,
    sort,
    toggleSort,
    groupBy,
    changeGroupBy,
    page: safePage,
    pageCount,
    pageGroups,
    groupCount,
    filteredCount: filteredEvents.length,
    selected,
    openDetail,
    closeDetail,
    changePage,
    isLoading: isPending && isFetching,
    error: error ?? null,
    refresh: refetch,
    isEmpty: allEvents.length === 0
  };
}
