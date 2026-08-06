import { useMemo, useState } from "react";
import { formatDateTime } from "../../lib/format";
import { useMachinesQuery } from "../../lib/useApiQueries";
import type {
  MachineExplorerFilters,
  MachineExplorerOptions,
  MachineExplorerSort,
  MachineExplorerSortColumn,
  MachineRecord
} from "./machineExplorer.types";

export const emptyMachineExplorerFilters: MachineExplorerFilters = {
  query: "",
  status: ""
};

const SORTERS: Record<MachineExplorerSortColumn, (a: MachineRecord, b: MachineRecord) => number> = {
  machineId: (a, b) => a.machineId.localeCompare(b.machineId),
  healthScore: (a, b) => a.healthScore - b.healthScore,
  activeBatteries: (a, b) => a.activeBatteries - b.activeBatteries,
  lastSeen: (a, b) => a.lastSeen.localeCompare(b.lastSeen)
};

function matchesFilters(record: MachineRecord, filters: MachineExplorerFilters): boolean {
  const query = filters.query.trim().toLowerCase();

  if (query && !record.machineId.toLowerCase().includes(query) && !record.name.toLowerCase().includes(query)) {
    return false;
  }

  if (filters.status && record.status !== filters.status) {
    return false;
  }

  return true;
}

function deriveOptions(records: MachineRecord[]): MachineExplorerOptions {
  return {
    statuses: [...new Set(records.map((record) => record.status))].sort()
  };
}

function countActiveFilters(filters: MachineExplorerFilters): number {
  return Object.values(filters).filter((value) => value.trim().length > 0).length;
}

export function useMachineExplorer() {
  const { data, error, isPending, isFetching, refetch } = useMachinesQuery();

  const allMachines = useMemo<MachineRecord[]>(
    () =>
      (data ?? []).map((machine) => ({
        id: `machine-${machine.name}`,
        machineId: machine.name,
        name: machine.name,
        status: machine.status === "Offline" ? "Offline" : "Online",
        slotCount: 0,
        activeBatteries: 0,
        pendingRemovalCount: 0,
        finalizedCount: 0,
        healthScore: machine.health_score,
        lastSeen: formatDateTime(machine.last_seen),
        dominantFirmware: machine.firmware,
        slotsOccupied: 0,
        firmwareSummary: machine.firmware ? [{ firmware: machine.firmware, count: 0 }] : [],
        productDistribution: [],
        batteryCount: 0
      })),
    [data]
  );

  const [filters, setFilters] = useState<MachineExplorerFilters>(emptyMachineExplorerFilters);
  const [sort, setSort] = useState<MachineExplorerSort>({ column: "machineId", direction: "asc" });
  const [selected, setSelected] = useState<MachineRecord | null>(null);

  const options = useMemo(() => deriveOptions(allMachines), [allMachines]);

  const filteredMachines = useMemo(() => {
    const filtered = allMachines.filter((record) => matchesFilters(record, filters));
    const sorted = filtered.slice().sort((a, b) => {
      const result = SORTERS[sort.column](a, b);
      return sort.direction === "asc" ? result : -result;
    });

    return sorted;
  }, [allMachines, filters, sort]);

  const activeFilterCount = countActiveFilters(filters);

  const updateFilters = (patch: Partial<MachineExplorerFilters>) => {
    setFilters((current) => ({ ...current, ...patch }));
  };

  const clearFilters = () => {
    setFilters(emptyMachineExplorerFilters);
  };

  const toggleSort = (column: MachineExplorerSortColumn) => {
    setSort((current) =>
      current.column === column
        ? { column, direction: current.direction === "asc" ? "desc" : "asc" }
        : { column, direction: "asc" }
    );
  };

  const openDetail = (record: MachineRecord) => setSelected(record);
  const closeDetail = () => setSelected(null);

  return {
    allMachines,
    options,
    filters,
    updateFilters,
    clearFilters,
    activeFilterCount,
    sort,
    toggleSort,
    filteredCount: filteredMachines.length,
    filteredMachines,
    selected,
    openDetail,
    closeDetail,
    isLoading: isPending && isFetching,
    error: error ?? null,
    refresh: refetch,
    isEmpty: allMachines.length === 0
  };
}
