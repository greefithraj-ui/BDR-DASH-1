import { useMemo, useState } from "react";
import { getHealthTimeline, getMockAdministration } from "./administration.mock";
import type {
  AdministrationFilters,
  AdministrationOptions,
  AuditEntry,
  HealthTimelinePoint,
  MachineRecord
} from "./administration.types";

export const emptyAdministrationFilters: AdministrationFilters = {
  search: "",
  status: "",
  connection: "",
  fromDate: "",
  toDate: ""
};

function matchesFilters(machine: MachineRecord, filters: AdministrationFilters): boolean {
  const search = filters.search.trim().toLowerCase();

  if (
    search &&
    !machine.machineId.toLowerCase().includes(search) &&
    !machine.machineName.toLowerCase().includes(search) &&
    !machine.firmware.toLowerCase().includes(search) &&
    !machine.collectorVersion.toLowerCase().includes(search)
  ) {
    return false;
  }

  if (filters.status && machine.status !== filters.status) {
    return false;
  }

  if (filters.connection && machine.connection !== filters.connection) {
    return false;
  }

  if (filters.fromDate && machine.lastSeen < filters.fromDate) {
    return false;
  }

  if (filters.toDate && machine.lastSeen > filters.toDate) {
    return false;
  }

  return true;
}

function deriveOptions(machines: MachineRecord[]): AdministrationOptions {
  return {
    statuses: [...new Set(machines.map((machine) => machine.status))].sort(),
    connections: [...new Set(machines.map((machine) => machine.connection))].sort()
  };
}

function countActiveFilters(filters: AdministrationFilters): number {
  return Object.values(filters).filter((value) => value.trim().length > 0).length;
}

export function useAdministration() {
  const data = useMemo(() => getMockAdministration(), []);
  const allMachines = data.machines;

  const [filters, setFilters] = useState<AdministrationFilters>(emptyAdministrationFilters);
  const [selected, setSelected] = useState<MachineRecord | null>(null);

  const options = useMemo(() => deriveOptions(allMachines), [allMachines]);

  const filteredMachines = useMemo(
    () => allMachines.filter((machine) => matchesFilters(machine, filters)),
    [allMachines, filters]
  );

  const activeFilterCount = countActiveFilters(filters);

  const machineTimeline: HealthTimelinePoint[] = useMemo(
    () => (selected ? getHealthTimeline(selected.machineId) : []),
    [selected]
  );

  const machineAuditEntries: AuditEntry[] = useMemo(
    () => (selected ? data.auditEntries.filter((entry) => entry.entityId === selected.machineId) : []),
    [selected, data.auditEntries]
  );

  const updateFilters = (patch: Partial<AdministrationFilters>) => {
    setFilters((current) => ({ ...current, ...patch }));
  };

  const clearFilters = () => {
    setFilters(emptyAdministrationFilters);
  };

  const openDetail = (machine: MachineRecord) => setSelected(machine);
  const closeDetail = () => setSelected(null);

  return {
    machines: filteredMachines,
    allMachines,
    kpis: data.kpis,
    collectors: data.collectors,
    schemas: data.schemas,
    services: data.services,
    databases: data.databases,
    healthMetrics: data.healthMetrics,
    auditEntries: data.auditEntries,
    platform: data.platform,
    options,
    filters,
    updateFilters,
    clearFilters,
    activeFilterCount,
    selected,
    openDetail,
    closeDetail,
    machineTimeline,
    machineAuditEntries
  };
}
