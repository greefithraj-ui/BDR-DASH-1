export type AnalyticsTone = "neutral" | "success" | "warning" | "danger" | "info";

export type AnalyticsKpi = {
  id: string;
  label: string;
  value: string;
  delta: string;
  deltaTone: AnalyticsTone;
};

export type AnalyticsCategory = "machine" | "product" | "quality" | "reliability" | "performance" | "trend" | "comparison";

export type AnalyticsMetric = {
  label: string;
  value: string;
  tone?: AnalyticsTone;
};

export type AnalyticsCard = {
  id: string;
  category: AnalyticsCategory;
  title: string;
  description: string;
  status: string;
  statusTone: AnalyticsTone;
  route: string;
  metrics: AnalyticsMetric[];
  primaryAction: { label: string };
  secondaryAction: { label: string };
};

export type Insight = {
  id: string;
  title: string;
  detail: string;
  tag: string;
  tagTone: AnalyticsTone;
  timestamp: string;
};

export type Alert = {
  id: string;
  severity: AnalyticsTone;
  title: string;
  detail: string;
  timestamp: string;
};

export type QuickNavItem = {
  id: string;
  label: string;
  route: string;
  description: string;
};

export type AnalyticsChartPlaceholder = {
  id: string;
  title: string;
  description: string;
};
