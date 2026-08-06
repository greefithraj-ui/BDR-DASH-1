import type { HealthResponse } from "../../../../shared/contracts/health";

const API_BASE_URL = import.meta.env.VITE_BIP_API_BASE_URL ?? "/api";

export type SuccessEnvelope<T> = {
  data: T;
  meta: Record<string, string | number | null>;
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type ApiQuery = Record<string, string | number | undefined>;

export type MachineDto = {
  id: string;
  name: string;
  status: string;
  connection: string;
  health_score: number;
  firmware: string;
  last_seen: string;
};

export type RingDto = {
  id: string;
  name: string;
  status: string;
  capacity_mwh: number;
  installed_at: string;
};

export type ReportSummaryDto = {
  id: string;
  title: string;
  kind: string;
  status: string;
  generated_at: string;
};

export type TimelineEventDto = {
  id: string;
  timestamp: string;
  type: string;
  machine_id: string;
  message: string;
};

export type MetricDto = {
  id: string;
  name: string;
  value: number;
  unit: string;
  status: string;
};

export type AnalyticsSummaryDto = {
  id: string;
  key: string;
  label: string;
  value: number;
  unit: string;
};

export type QualitySummaryDto = {
  id: string;
  metric: string;
  value: number;
  target: number;
  status: string;
};

export type PerformanceSummaryDto = {
  id: string;
  metric: string;
  value: number;
  unit: string;
  status: string;
};

function buildQuery(params?: ApiQuery): string {
  const search = new URLSearchParams();

  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }

  const queryString = search.toString();
  return queryString ? `?${queryString}` : "";
}

async function request<TResponse>(path: string): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Accept: "application/json"
    }
  });

  if (!response.ok) {
    throw new Error(`BIP API request failed with status ${response.status}`);
  }

  return (await response.json()) as TResponse;
}

async function requestData<TData>(path: string): Promise<TData> {
  const envelope = await request<SuccessEnvelope<TData>>(path);
  return envelope.data;
}

export async function fetchAllPages<T>(
  fetchPage: (page: number) => Promise<PaginatedResponse<T>>,
  pageSize = 100
): Promise<T[]> {
  const first = await fetchPage(1);

  if (first.total <= pageSize) {
    return first.items;
  }

  const remainingPages = Math.ceil(first.total / pageSize) - 1;
  const pages = await Promise.all(
    Array.from({ length: remainingPages }, (_, index) => fetchPage(index + 2))
  );

  return [...first.items, ...pages.flatMap((page) => page.items)];
}

export const apiClient = {
  health: () => request<HealthResponse>("/health"),
  getMachines: (params?: ApiQuery) =>
    requestData<PaginatedResponse<MachineDto>>(`/v1/machines${buildQuery(params)}`),
  getMachine: (id: string) =>
    requestData<MachineDto>(`/v1/machines/${encodeURIComponent(id)}`),
  getRings: (params?: ApiQuery) =>
    requestData<PaginatedResponse<RingDto>>(`/v1/rings${buildQuery(params)}`),
  getRing: (id: string) =>
    requestData<RingDto>(`/v1/rings/${encodeURIComponent(id)}`),
  getReports: (params?: ApiQuery) =>
    requestData<PaginatedResponse<ReportSummaryDto>>(`/v1/reports${buildQuery(params)}`),
  getTimelineEvents: (params?: ApiQuery) =>
    requestData<PaginatedResponse<TimelineEventDto>>(`/v1/timeline${buildQuery(params)}`),
  getMetrics: (params?: ApiQuery) =>
    requestData<PaginatedResponse<MetricDto>>(`/v1/metrics${buildQuery(params)}`),
  getAnalyticsSummary: () =>
    requestData<PaginatedResponse<AnalyticsSummaryDto>>("/v1/analytics/summary"),
  getQualitySummary: () =>
    requestData<PaginatedResponse<QualitySummaryDto>>("/v1/quality/summary"),
  getPerformanceSummary: () =>
    requestData<PaginatedResponse<PerformanceSummaryDto>>("/v1/performance/summary")
};
