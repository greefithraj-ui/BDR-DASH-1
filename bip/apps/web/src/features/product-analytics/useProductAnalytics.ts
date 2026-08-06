import { useMemo, useState } from "react";
import { useAnalyticsSummaryQuery, useMachinesQuery, useQualitySummaryQuery } from "../../lib/useApiQueries";
import type {
  FailureDistributionItem,
  FleetLifecycleItem,
  ProductChartPlaceholder,
  ProductComparisonCard,
  ProductDistributionItem,
  ProductFilters,
  ProductFirmwareSummary,
  ProductKpi,
  ProductOptions,
  ProductRecord
} from "./productAnalytics.types";

type ProductAnalyticsData = {
  products: ProductRecord[];
  kpis: ProductKpi[];
  comparisonCards: ProductComparisonCard[];
  distribution: ProductDistributionItem[];
  failureDistribution: FailureDistributionItem[];
  fleetLifecycle: FleetLifecycleItem[];
  fleetFirmware: ProductFirmwareSummary[];
  charts: ProductChartPlaceholder[];
};

export const emptyProductFilters: ProductFilters = {
  product: "",
  firmware: "",
  machine: "",
  lifecycleState: "",
  dateFrom: "",
  dateTo: "",
  search: ""
};

const STATIC_CHARTS = [
  {
    id: "product-chart-firmware-trend",
    title: "Firmware Adoption Trend",
    description: "Placeholder chart container for future firmware adoption over time."
  },
  {
    id: "product-chart-failure-trend",
    title: "Failure Trend by Cause",
    description: "Placeholder chart container for future failure cause distribution."
  }
];

function matchesFilters(record: ProductRecord, filters: ProductFilters): boolean {
  const search = filters.search.trim().toLowerCase();

  if (
    search &&
    !record.product.toLowerCase().includes(search) &&
    !record.category.toLowerCase().includes(search) &&
    !record.description.toLowerCase().includes(search)
  ) {
    return false;
  }

  if (filters.product && record.product !== filters.product) {
    return false;
  }

  if (filters.firmware && !record.firmwareSummary.some((item) => item.firmware === filters.firmware)) {
    return false;
  }

  if (filters.machine && !record.machines.includes(filters.machine)) {
    return false;
  }

  if (filters.lifecycleState && !record.lifecycleDistribution.some((item) => item.stage === filters.lifecycleState)) {
    return false;
  }

  if (filters.dateFrom && record.lastUpdated < filters.dateFrom) {
    return false;
  }

  if (filters.dateTo && record.lastUpdated > filters.dateTo) {
    return false;
  }

  return true;
}

function deriveOptions(products: ProductRecord[]): ProductOptions {
  const unique = (values: string[]): string[] => [...new Set(values)].sort();

  return {
    products: unique(products.map((product) => product.product)),
    firmwares: unique(products.flatMap((product) => product.firmwareSummary.map((item) => item.firmware))),
    machines: unique(products.flatMap((product) => product.machines)),
    lifecycleStates: unique(products.flatMap((product) => product.lifecycleDistribution.map((item) => item.stage)))
  };
}

function countActiveFilters(filters: ProductFilters): number {
  return Object.values(filters).filter((value) => value.trim().length > 0).length;
}

export function useProductAnalytics() {
  const quality = useQualitySummaryQuery();
  const analytics = useAnalyticsSummaryQuery();
  const machines = useMachinesQuery();

  const queries = [quality, analytics, machines];

  const isLoading = queries.some((query) => query.isPending && query.isFetching);
  const error = queries.find((query) => query.error)?.error ?? null;
  const refresh = () => Promise.all(queries.map((query) => query.refetch()));

  const data = useMemo<ProductAnalyticsData>(() => {
    const qualityItem = (id: string) => quality.data?.items.find((item) => item.id === id);
    const analyticsItem = (key: string) => analytics.data?.items.find((item) => item.key === key);

    const activeRings = analyticsItem("active_rings")?.value ?? 0;
    const passRate = qualityItem("QL-1")?.value ?? 0;
    const healthScores = (machines.data ?? []).map((machine) => machine.health_score);
    const averageHealth = healthScores.length > 0 ? Math.round(healthScores.reduce((sum, score) => sum + score, 0) / healthScores.length) : 0;

    const firmwareCounts = new Map<string, number>();
    for (const machine of machines.data ?? []) {
      if (machine.firmware) {
        firmwareCounts.set(machine.firmware, (firmwareCounts.get(machine.firmware) ?? 0) + 1);
      }
    }

    const fleetFirmware = [...firmwareCounts.entries()]
      .map(([firmware, count]) => ({ firmware, count }))
      .sort((a, b) => b.count - a.count);

    return {
      products: [] as ProductRecord[],
      kpis: [
        { id: "kpi-products", label: "Products", value: "0", delta: "Across 3 categories", deltaTone: "info" as const },
        { id: "kpi-total", label: "Total Batteries", value: String(Math.round(activeRings)), delta: "+118 this month", deltaTone: "success" as const },
        { id: "kpi-pass-rate", label: "Avg Pass Rate", value: `${passRate}%`, delta: "+0.3 pts", deltaTone: "success" as const },
        { id: "kpi-health", label: "Fleet Health", value: `${averageHealth}/100`, delta: "+1 pt", deltaTone: "success" as const }
      ],
      comparisonCards: [],
      distribution: [],
      failureDistribution: [],
      fleetLifecycle: [],
      fleetFirmware,
      charts: STATIC_CHARTS
    } satisfies ProductAnalyticsData;
  }, [quality.data, analytics.data, machines.data]);

  const allProducts = data.products;

  const [filters, setFilters] = useState<ProductFilters>(emptyProductFilters);
  const [selected, setSelected] = useState<ProductRecord | null>(null);

  const options = useMemo(() => deriveOptions(allProducts), [allProducts]);

  const filteredProducts = useMemo(() => allProducts.filter((product) => matchesFilters(product, filters)), [allProducts, filters]);

  const activeFilterCount = countActiveFilters(filters);

  const updateFilters = (patch: Partial<ProductFilters>) => {
    setFilters((current) => ({ ...current, ...patch }));
  };

  const clearFilters = () => {
    setFilters(emptyProductFilters);
  };

  const openDetail = (product: ProductRecord) => setSelected(product);
  const closeDetail = () => setSelected(null);

  return {
    products: filteredProducts,
    kpis: data.kpis,
    comparisonCards: data.comparisonCards,
    distribution: data.distribution,
    failureDistribution: data.failureDistribution,
    fleetLifecycle: data.fleetLifecycle,
    fleetFirmware: data.fleetFirmware,
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
    isEmpty: allProducts.length === 0
  };
}