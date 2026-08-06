import { useMemo, useState } from "react";
import { getMockPerformanceAnalytics } from "./performanceAnalytics.mock";
import type { PerformanceFilters, PerformanceOptions, PerformanceRecord } from "./performanceAnalytics.types";

export const emptyPerformanceFilters: PerformanceFilters = {
  machine: "",
  product: "",
  firmware: "",
  dateFrom: "",
  dateTo: "",
  search: ""
};

function matchesFilters(record: PerformanceRecord, filters: PerformanceFilters): boolean {
  const search = filters.search.trim().toLowerCase();

  if (
    search &&
    !record.machine.toLowerCase().includes(search) &&
    !record.product.toLowerCase().includes(search) &&
    !record.category.toLowerCase().includes(search) &&
    !record.firmware.toLowerCase().includes(search)
  ) {
    return false;
  }

  if (filters.machine && record.machine !== filters.machine) {
    return false;
  }

  if (filters.product && record.product !== filters.product) {
    return false;
  }

  if (filters.firmware && record.firmware !== filters.firmware) {
    return false;
  }

  if (filters.dateFrom && record.date < filters.dateFrom) {
    return false;
  }

  if (filters.dateTo && record.date > filters.dateTo) {
    return false;
  }

  return true;
}

function deriveOptions(records: PerformanceRecord[]): PerformanceOptions {
  const unique = (values: string[]): string[] => [...new Set(values)].sort();

  return {
    machines: unique(records.map((record) => record.machine)),
    products: unique(records.map((record) => record.product)),
    firmwares: unique(records.map((record) => record.firmware))
  };
}

function countActiveFilters(filters: PerformanceFilters): number {
  return Object.values(filters).filter((value) => value.trim().length > 0).length;
}

export function usePerformanceAnalytics() {
  const data = useMemo(() => getMockPerformanceAnalytics(), []);
  const allRecords = data.records;

  const [filters, setFilters] = useState<PerformanceFilters>(emptyPerformanceFilters);
  const [selected, setSelected] = useState<PerformanceRecord | null>(null);

  const options = useMemo(() => deriveOptions(allRecords), [allRecords]);

  const filteredRecords = useMemo(() => allRecords.filter((record) => matchesFilters(record, filters)), [allRecords, filters]);

  const activeFilterCount = countActiveFilters(filters);

  const updateFilters = (patch: Partial<PerformanceFilters>) => {
    setFilters((current) => ({ ...current, ...patch }));
  };

  const clearFilters = () => {
    setFilters(emptyPerformanceFilters);
  };

  const openDetail = (record: PerformanceRecord) => setSelected(record);
  const closeDetail = () => setSelected(null);

  return {
    records: filteredRecords,
    kpis: data.kpis,
    cycleDistribution: data.cycleDistribution,
    utilizationDistribution: data.utilizationDistribution,
    trend: data.trend,
    machineComparisons: data.machineComparisons,
    productComparisons: data.productComparisons,
    charts: data.charts,
    options,
    filters,
    updateFilters,
    clearFilters,
    activeFilterCount,
    selected,
    openDetail,
    closeDetail
  };
}
