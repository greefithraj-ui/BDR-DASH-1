import { useMemo, useState } from "react";
import { formatDateTime } from "../../lib/format";
import { useRingsQuery } from "../../lib/useApiQueries";
import type {
  BatteryExplorerFilters,
  BatteryRecord,
  ExplorerOptions,
  ExplorerSort,
  ExplorerSortColumn
} from "./batteryExplorer.types";

export const BATTERY_EXPLORER_PAGE_SIZE = 10;

export const emptyBatteryExplorerFilters: BatteryExplorerFilters = {
  serialNumberQuery: "",
  ringMacQuery: "",
  ringNameQuery: "",
  product: "",
  machine: "",
  slot: "",
  state: "",
  firmware: "",
  dateFrom: "",
  dateTo: ""
};

const SORTERS: Record<ExplorerSortColumn, (a: BatteryRecord, b: BatteryRecord) => number> = {
  serialNumber: (a, b) => a.serialNumber.localeCompare(b.serialNumber),
  ringName: (a, b) => a.ringName.localeCompare(b.ringName),
  product: (a, b) => a.product.localeCompare(b.product),
  machine: (a, b) => a.machine.localeCompare(b.machine),
  currentState: (a, b) => a.currentState.localeCompare(b.currentState),
  firmware: (a, b) => a.firmware.localeCompare(b.firmware),
  firstSeen: (a, b) => a.firstSeen.localeCompare(b.firstSeen),
  lastSeen: (a, b) => a.lastSeen.localeCompare(b.lastSeen)
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

function matchesFilters(record: BatteryRecord, filters: BatteryExplorerFilters): boolean {
  const serialQuery = filters.serialNumberQuery.trim().toLowerCase();
  const ringMacQuery = filters.ringMacQuery.trim().toLowerCase();
  const ringNameQuery = filters.ringNameQuery.trim().toLowerCase();

  if (serialQuery && !record.serialNumber.toLowerCase().includes(serialQuery)) {
    return false;
  }

  if (ringMacQuery && !record.ringMac.toLowerCase().includes(ringMacQuery)) {
    return false;
  }

  if (ringNameQuery && !record.ringName.toLowerCase().includes(ringNameQuery)) {
    return false;
  }

  if (filters.product && record.product !== filters.product) {
    return false;
  }

  if (filters.machine && record.machine !== filters.machine) {
    return false;
  }

  if (filters.slot && record.slot !== filters.slot) {
    return false;
  }

  if (filters.state && record.currentState !== filters.state) {
    return false;
  }

  if (filters.firmware && record.firmware !== filters.firmware) {
    return false;
  }

  const lastSeenDate = record.lastSeen.slice(0, 10);

  if (filters.dateFrom && lastSeenDate < filters.dateFrom) {
    return false;
  }

  if (filters.dateTo && lastSeenDate > filters.dateTo) {
    return false;
  }

  return true;
}

function deriveOptions(records: BatteryRecord[]): ExplorerOptions {
  const unique = (values: string[]): string[] => [...new Set(values)].sort();

  return {
    products: unique(records.map((record) => record.product)),
    machines: unique(records.map((record) => record.machine)),
    slots: unique(records.map((record) => record.slot)),
    states: unique(records.map((record) => record.currentState)),
    firmwares: unique(records.map((record) => record.firmware))
  };
}

function countActiveFilters(filters: BatteryExplorerFilters): number {
  return Object.values(filters).filter((value) => value.trim().length > 0).length;
}

export function useBatteryExplorer() {
  const { data, error, isPending, isFetching, refetch } = useRingsQuery();

  const allRecords = useMemo<BatteryRecord[]>(
    () =>
      (data ?? []).map((ring, index) => {
        const currentState = STATE_FROM_RING_STATUS[ring.status] ?? "Tracking";
        const seen = formatDateTime(ring.installed_at);

        return {
          id: `battery-${index + 1}`,
          serialNumber: ring.id,
          ringMac: ring.id,
          ringName: ring.name,
          product: "",
          machine: "",
          slot: "",
          currentState,
          firmware: "",
          firstSeen: seen,
          lastSeen: seen,
          lifecycleStatus: LIFECYCLE_BY_STATE[currentState] ?? "In Progress",
          tone: TONE_BY_STATE[currentState] ?? "neutral"
        };
      }),
    [data]
  );

  const [filters, setFilters] = useState<BatteryExplorerFilters>(emptyBatteryExplorerFilters);
  const [sort, setSort] = useState<ExplorerSort>({ column: "lastSeen", direction: "desc" });
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<BatteryRecord | null>(null);

  const options = useMemo(() => deriveOptions(allRecords), [allRecords]);

  const filteredRecords = useMemo(() => {
    const filtered = allRecords.filter((record) => matchesFilters(record, filters));
    const sorted = filtered.slice().sort((a, b) => {
      const result = SORTERS[sort.column](a, b);
      return sort.direction === "asc" ? result : -result;
    });

    return sorted;
  }, [allRecords, filters, sort]);

  const pageCount = Math.max(1, Math.ceil(filteredRecords.length / BATTERY_EXPLORER_PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const pageRecords = filteredRecords.slice(
    (safePage - 1) * BATTERY_EXPLORER_PAGE_SIZE,
    safePage * BATTERY_EXPLORER_PAGE_SIZE
  );

  const activeFilterCount = countActiveFilters(filters);

  const updateFilters = (patch: Partial<BatteryExplorerFilters>) => {
    setFilters((current) => ({ ...current, ...patch }));
    setPage(1);
  };

  const clearFilters = () => {
    setFilters(emptyBatteryExplorerFilters);
    setPage(1);
  };

  const removeFilter = (key: keyof BatteryExplorerFilters) => {
    setFilters((current) => ({ ...current, [key]: "" }));
    setPage(1);
  };

  const toggleSort = (column: ExplorerSortColumn) => {
    setSort((current) =>
      current.column === column
        ? { column, direction: current.direction === "asc" ? "desc" : "asc" }
        : { column, direction: "asc" }
    );
    setPage(1);
  };

  const changePage = (nextPage: number) => {
    setPage(Math.max(1, Math.min(nextPage, pageCount)));
  };

  const openDetail = (record: BatteryRecord) => setSelected(record);
  const closeDetail = () => setSelected(null);

  return {
    allRecords,
    options,
    filters,
    updateFilters,
    clearFilters,
    removeFilter,
    activeFilterCount,
    sort,
    toggleSort,
    page: safePage,
    pageCount,
    pageRecords,
    filteredCount: filteredRecords.length,
    selected,
    openDetail,
    closeDetail,
    changePage,
    isLoading: isPending && isFetching,
    error: error ?? null,
    refresh: refetch,
    isEmpty: allRecords.length === 0
  };
}
