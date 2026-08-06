export type DashboardTone = "neutral" | "success" | "warning" | "danger" | "info";

export type ExecutiveKpi = {
  id: string;
  label: string;
  value: string;
  helper: string;
  tone: DashboardTone;
};

export type OperationsOverviewItem = {
  id: string;
  title: string;
  value: string;
  description: string;
  tone: DashboardTone;
};

export type RecentActivityItem = {
  id: string;
  title: string;
  context: string;
  timestamp: string;
};

export type ExecutiveAlert = {
  id: string;
  title: string;
  description: string;
  severity: "info" | "warning" | "danger";
};

export type PerformancePlaceholder = {
  id: string;
  title: string;
  description: string;
};

export type ExecutiveDashboardData = {
  kpis: ExecutiveKpi[];
  operations: OperationsOverviewItem[];
  activity: RecentActivityItem[];
  alerts: ExecutiveAlert[];
  performance: PerformancePlaceholder[];
};
