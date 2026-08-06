import { useMemo, useState } from "react";
import { formatDate, formatDateTime } from "../../lib/format";
import { useReportsQuery } from "../../lib/useApiQueries";
import type { Report, ReportsFilters, ReportsOptions } from "./reports.types";

export const emptyReportsFilters: ReportsFilters = {
  search: "",
  category: "",
  status: "",
  owner: "",
  frequency: "",
  dateFrom: "",
  dateTo: ""
};

const REPORT_DESCRIPTION =
  "Live snapshot of the most recent ring data collected from the machine.";

function matchesFilters(report: Report, filters: ReportsFilters): boolean {
  const search = filters.search.trim().toLowerCase();

  if (
    search &&
    !report.title.toLowerCase().includes(search) &&
    !report.description.toLowerCase().includes(search) &&
    !report.category.toLowerCase().includes(search) &&
    !report.owner.toLowerCase().includes(search)
  ) {
    return false;
  }

  if (filters.category && report.category !== filters.category) {
    return false;
  }

  if (filters.status && report.status !== filters.status) {
    return false;
  }

  if (filters.owner && report.owner !== filters.owner) {
    return false;
  }

  if (filters.frequency && report.frequency !== filters.frequency) {
    return false;
  }

  if (filters.dateFrom && report.lastRun < filters.dateFrom) {
    return false;
  }

  if (filters.dateTo && report.lastRun > filters.dateTo) {
    return false;
  }

  return true;
}

function deriveOptions(reports: Report[]): ReportsOptions {
  const unique = (values: string[]): string[] => [...new Set(values)].sort();

  return {
    categories: unique(reports.map((report) => report.category)),
    statuses: unique(reports.map((report) => report.status)),
    owners: unique(reports.map((report) => report.owner)),
    frequencies: unique(reports.map((report) => report.frequency))
  };
}

function countActiveFilters(filters: ReportsFilters): number {
  return Object.values(filters).filter((value) => value.trim().length > 0).length;
}

function byRecent(a: Report, b: Report): number {
  return a.lastRun < b.lastRun ? 1 : -1;
}

export function useReports() {
  const { data, error, isPending, isFetching, refetch } = useReportsQuery();

  const queryData = useMemo(() => {
    const reports = (data ?? []).map<Report>((summary) => ({
      id: summary.id,
      title: summary.title,
      description: REPORT_DESCRIPTION,
      category: "Machine",
      owner: "Machine Ops",
      createdDate: formatDate(summary.generated_at),
      lastRun: formatDateTime(summary.generated_at),
      nextScheduledRun: "-",
      status: summary.status === "Scheduled" ? "Scheduled" : "Ready",
      statusTone: summary.status === "Scheduled" ? "info" : "success",
      frequency: "On Demand",
      estimatedDurationSeconds: 0,
      pages: 1,
      schedule: { time: "-", days: "On demand", recipients: [] },
      previewTables: [],
      history: []
    }));

    const scheduled = reports.filter((report) => report.status === "Scheduled").length;

    return {
      reports,
      kpis: [
        { id: "reports-kpi-total", label: "Total Reports", value: String(reports.length), delta: "Across 8 categories", deltaTone: "info" as const },
        { id: "reports-kpi-scheduled", label: "Scheduled Reports", value: String(scheduled), delta: "2 this week", deltaTone: "success" as const },
        { id: "reports-kpi-success", label: "Successful Runs", value: "0", delta: "+8 this month", deltaTone: "success" as const },
        { id: "reports-kpi-failed", label: "Failed Runs", value: "0", delta: "-2 this month", deltaTone: "warning" as const },
        { id: "reports-kpi-duration", label: "Average Duration", value: "0s", delta: "-5s", deltaTone: "success" as const }
      ],
      historyEntries: []
    };
  }, [data]);

  const allReports = queryData.reports;

  const [filters, setFilters] = useState<ReportsFilters>(emptyReportsFilters);
  const [selected, setSelected] = useState<Report | null>(null);

  const options = useMemo(() => deriveOptions(allReports), [allReports]);

  const filteredReports = useMemo(() => allReports.filter((report) => matchesFilters(report, filters)), [allReports, filters]);

  const activeFilterCount = countActiveFilters(filters);

  const recentReports = useMemo(() => [...filteredReports].sort(byRecent).slice(0, 3), [filteredReports]);
  const scheduledReports = useMemo(() => filteredReports.filter((report) => report.status === "Scheduled"), [filteredReports]);
  const previewReport = filteredReports[0] ?? allReports[0];

  const updateFilters = (patch: Partial<ReportsFilters>) => {
    setFilters((current) => ({ ...current, ...patch }));
  };

  const clearFilters = () => {
    setFilters(emptyReportsFilters);
  };

  const openDetail = (report: Report) => setSelected(report);
  const closeDetail = () => setSelected(null);

  return {
    reports: filteredReports,
    recentReports,
    scheduledReports,
    previewReport,
    kpis: queryData.kpis,
    historyEntries: queryData.historyEntries,
    options,
    filters,
    updateFilters,
    clearFilters,
    activeFilterCount,
    selected,
    openDetail,
    closeDetail,
    isLoading: isPending && isFetching,
    error: error ?? null,
    refresh: refetch,
    isEmpty: allReports.length === 0
  };
}
