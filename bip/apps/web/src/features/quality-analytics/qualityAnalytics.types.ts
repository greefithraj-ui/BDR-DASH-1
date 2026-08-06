export type QualityTone = "neutral" | "success" | "warning" | "danger" | "info";

export type QualityResult = "Pass" | "Fail";

export type QualitySeverity = "Critical" | "High" | "Medium" | "Low";

export type QualityDefect = {
  id: string;
  category: string;
  count: number;
  tone: QualityTone;
};

export type QualityRecord = {
  id: string;
  product: string;
  category: string;
  machine: string;
  firmware: string;
  date: string;
  produced: number;
  passed: number;
  failed: number;
  retested: number;
  passRate: number;
  failRate: number;
  yield: number;
  retestRate: number;
  qualityScore: number;
  result: QualityResult;
  status: string;
  statusTone: QualityTone;
  defects: QualityDefect[];
};

export type QualityFilters = {
  product: string;
  machine: string;
  firmware: string;
  result: string;
  dateFrom: string;
  dateTo: string;
  search: string;
};

export type QualityOptions = {
  products: string[];
  machines: string[];
  firmwares: string[];
  results: string[];
};

export type QualityKpi = {
  id: string;
  label: string;
  value: string;
  delta: string;
  deltaTone: QualityTone;
};

export type QualityMetric = {
  label: string;
  value: string;
  tone?: QualityTone;
};

export type QualityComparisonItem = {
  id: string;
  name: string;
  kind: "Product" | "Machine";
  metrics: QualityMetric[];
  statusTone: QualityTone;
};

export type QualityDefectDistributionItem = {
  category: string;
  count: number;
  share: number;
  tone: QualityTone;
};

export type QualityFailureCategoryItem = {
  id: string;
  category: string;
  severity: QualitySeverity;
  tone: QualityTone;
  description: string;
  count: number;
  share: number;
};

export type QualityTrendPoint = {
  date: string;
  passRate: number;
  yield: number;
  failed: number;
};

export type QualityChartPlaceholder = {
  id: string;
  title: string;
  description: string;
};
