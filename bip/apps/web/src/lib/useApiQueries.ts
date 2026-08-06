import { useQuery } from "@tanstack/react-query";
import { apiClient, fetchAllPages } from "./apiClient";
import { queryKeys } from "./queryKeys";

const DATA_STALE_TIME = 30_000;

export function useMetricsQuery() {
  return useQuery({
    queryKey: queryKeys.metrics.all,
    queryFn: () => apiClient.getMetrics({ page_size: 100 }),
    staleTime: DATA_STALE_TIME
  });
}

export function useAnalyticsSummaryQuery() {
  return useQuery({
    queryKey: queryKeys.analyticsSummary.all,
    queryFn: () => apiClient.getAnalyticsSummary(),
    staleTime: DATA_STALE_TIME
  });
}

export function useQualitySummaryQuery() {
  return useQuery({
    queryKey: queryKeys.qualitySummary.all,
    queryFn: () => apiClient.getQualitySummary(),
    staleTime: DATA_STALE_TIME
  });
}

export function usePerformanceSummaryQuery() {
  return useQuery({
    queryKey: queryKeys.performanceSummary.all,
    queryFn: () => apiClient.getPerformanceSummary(),
    staleTime: DATA_STALE_TIME
  });
}

export function useHealthQuery() {
  return useQuery({
    queryKey: queryKeys.health.all,
    queryFn: () => apiClient.health(),
    staleTime: DATA_STALE_TIME
  });
}

export function useMachinesQuery() {
  return useQuery({
    queryKey: queryKeys.machines.all,
    queryFn: async () => (await apiClient.getMachines({ page_size: 100 })).items,
    staleTime: DATA_STALE_TIME
  });
}

export function useRingsQuery() {
  return useQuery({
    queryKey: queryKeys.rings.all,
    queryFn: () => fetchAllPages((page) => apiClient.getRings({ page, page_size: 100 })),
    staleTime: DATA_STALE_TIME
  });
}

export function useTimelineQuery() {
  return useQuery({
    queryKey: queryKeys.timeline.list,
    queryFn: () => fetchAllPages((page) => apiClient.getTimelineEvents({ page, page_size: 100 })),
    staleTime: DATA_STALE_TIME
  });
}

export function useReportsQuery() {
  return useQuery({
    queryKey: queryKeys.reports.list,
    queryFn: () => fetchAllPages((page) => apiClient.getReports({ page, page_size: 100 })),
    staleTime: DATA_STALE_TIME
  });
}
