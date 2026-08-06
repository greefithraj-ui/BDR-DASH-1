import { useMemo, useState } from "react";
import { useMachinesQuery, useQualitySummaryQuery } from "../../lib/useApiQueries";
import type {
  QualityChartPlaceholder,
  QualityComparisonItem,
  QualityDefectDistributionItem,
  QualityFailureCategoryItem,
  QualityFilters,
  QualityKpi,
  QualityOptions,
  QualityRecord,
  QualityTone,
  QualityTrendPoint
} from "./qualityAnalytics.types";

type QualityAnalyticsData = {
  records: QualityRecord[];
  kpis: QualityKpi[];
  defectDistribution: QualityDefectDistributionItem[];
  failureCategories: QualityFailureCategoryItem[];
  trend: QualityTrendPoint[];
  productComparisons: QualityComparisonItem[];
  machineComparisons: QualityComparisonItem[];
  charts: QualityChartPlaceholder[];
};

export const emptyQualityFilters: QualityFilters = {
  product: "",
  machine: "",
  firmware: "",
  result: "",
  dateFrom: "",
  dateTo: "",
  search: ""
};

const STATIC_CHARTS = [
  { id: "quality-chart-pass-trend", title: "Pass Rate Trend", description: "Placeholder chart container for pass rate over time." },
  { id: "quality-chart-yield-trend", title: "Yield Trend", description: "Placeholder chart container for yield over time." },
  { id: "quality-chart-defect-volume", title: "Defect Volume by Category", description: "Placeholder chart container for defect volume by failure category." }
];

function matchesFilters(record: QualityRecord, filters: QualityFilters): boolean {
  const search = filters.search.trim().toLowerCase();

  if (
    search &&
    !record.product.toLowerCase().includes(search) &&
    !record.category.toLowerCase().includes(search) &&
    !record.machine.toLowerCase().includes(search) &&
    !record.firmware.toLowerCase().includes(search)
  ) {
    return false;
  }

  if (filters.product && record.product !== filters.product) {
    return false;
  }

  if (filters.machine && record.machine !== filters.machine) {
    return false;
  }

  if (filters.firmware && record.firmware !== filters.firmware) {
    return false;
  }

  if (filters.result && record.result !== filters.result) {
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

function deriveOptions(records: QualityRecord[]): QualityOptions {
  const unique = (values: string[]): string[] => [...new Set(values)].sort();

  return {
    products: unique(records.map((record) => record.product)),
    machines: unique(records.map((record) => record.machine)),
    firmwares: unique(records.map((record) => record.firmware)),
    results: unique(records.map((record) => record.result))
  };
}

function countActiveFilters(filters: QualityFilters): number {
  return Object.values(filters).filter((value) => value.trim().length > 0).length;
}

export function useQualityAnalytics() {
  const quality = useQualitySummaryQuery();
  const machines = useMachinesQuery();

  const queries = [quality, machines];

  const isLoading = queries.some((query) => query.isPending && query.isFetching);
  const error = queries.find((query) => query.error)?.error ?? null;
  const refresh = () => Promise.all(queries.map((query) => query.refetch()));

  const data = useMemo<QualityAnalyticsData>(() => {
    const qualityItem = (id: string) => quality.data?.items.find((item) => item.id === id);

    const passRate = qualityItem("QL-1")?.value ?? 0;
    const failedSlots = qualityItem("QL-2")?.value ?? 0;
    const completedSlots = qualityItem("QL-5")?.value ?? 0;
    const failRate = completedSlots > 0 ? Math.round((failedSlots / completedSlots) * 1000) / 10 : 0;
    const healthScores = (machines.data ?? []).map((machine) => machine.health_score);
    const averageHealth = healthScores.length > 0 ? Math.round(healthScores.reduce((sum, score) => sum + score, 0) / healthScores.length) : 0;

    const machineComparisons: QualityComparisonItem[] = (machines.data ?? []).map((machine) => {
      const scoreTone: QualityTone = machine.health_score >= 80 ? "success" : machine.health_score >= 60 ? "info" : "warning";

      return {
        id: `machine-comparison-${machine.name}`,
        name: machine.name,
        kind: "Machine",
        statusTone: machine.status === "Offline" ? "danger" : machine.health_score >= 80 ? "success" : "warning",
        metrics: [
          { label: "Health Score", value: `${Math.round(machine.health_score)}/100`, tone: scoreTone },
          { label: "Connection", value: machine.connection, tone: machine.connection === "Online" ? "success" : "danger" },
          { label: "Firmware", value: machine.firmware || "Not reported" }
        ]
      };
    });

    return {
      records: [] as QualityRecord[],
      kpis: [
        { id: "quality-kpi-pass-rate", label: "Pass Rate", value: `${passRate}%`, delta: "+0.4 pts", deltaTone: "success" as const },
        { id: "quality-kpi-fail-rate", label: "Fail Rate", value: `${failRate}%`, delta: "-0.2 pts", deltaTone: "success" as const },
        { id: "quality-kpi-yield", label: "Yield", value: `${passRate}%`, delta: "+0.3 pts", deltaTone: "success" as const },
        { id: "quality-kpi-retest-rate", label: "Retest Rate", value: "0%", delta: "-1.1 pts", deltaTone: "success" as const },
        { id: "quality-kpi-score", label: "Quality Score", value: `${Math.round(passRate)}/100`, delta: "+2 pts", deltaTone: "success" as const }
      ],
      defectDistribution: [],
      failureCategories: [],
      trend: [],
      productComparisons: [],
      machineComparisons,
      charts: STATIC_CHARTS
    } satisfies QualityAnalyticsData;
  }, [quality.data, machines.data]);

  const allRecords = data.records;

  const [filters, setFilters] = useState<QualityFilters>(emptyQualityFilters);
  const [selected, setSelected] = useState<QualityRecord | null>(null);

  const options = useMemo(() => deriveOptions(allRecords), [allRecords]);

  const filteredRecords = useMemo(() => allRecords.filter((record) => matchesFilters(record, filters)), [allRecords, filters]);

  const activeFilterCount = countActiveFilters(filters);

  const updateFilters = (patch: Partial<QualityFilters>) => {
    setFilters((current) => ({ ...current, ...patch }));
  };

  const clearFilters = () => {
    setFilters(emptyQualityFilters);
  };

  const openDetail = (record: QualityRecord) => setSelected(record);
  const closeDetail = () => setSelected(null);

  return {
    records: filteredRecords,
    kpis: data.kpis,
    defectDistribution: data.defectDistribution,
    failureCategories: data.failureCategories,
    trend: data.trend,
    productComparisons: data.productComparisons,
    machineComparisons: data.machineComparisons,
    charts: data.charts,
    options,
    filters,
    updateFilters,
    clearFilters,
    activeFilterCount,
    selected,
    openDetail,
    closeDetail,
    isLoading,
    error,
    refresh,
    isEmpty: allRecords.length === 0
  };
}