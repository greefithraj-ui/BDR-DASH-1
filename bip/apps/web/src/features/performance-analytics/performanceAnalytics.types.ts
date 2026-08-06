export type PerformanceTone = "neutral" | "success" | "warning" | "danger" | "info";

export type PerformanceRecord = {
  id: string;
  machine: string;
  product: string;
  category: string;
  firmware: string;
  date: string;
  produced: number;
  throughput: number;
  cycleTime: number;
  utilization: number;
  processingRate: number;
  efficiency: number;
  performanceScore: number;
  targetThroughput: number;
  status: string;
  statusTone: PerformanceTone;
};

export type PerformanceFilters = {
  machine: string;
  product: string;
  firmware: string;
  dateFrom: string;
  dateTo: string;
  search: string;
};

export type PerformanceOptions = {
  machines: string[];
  products: string[];
  firmwares: string[];
};

export type PerformanceKpi = {
  id: string;
  label: string;
  value: string;
  delta: string;
  deltaTone: PerformanceTone;
};

export type PerformanceMetric = {
  label: string;
  value: string;
  tone?: PerformanceTone;
};

export type PerformanceComparisonItem = {
  id: string;
  name: string;
  kind: "Machine" | "Product";
  metrics: PerformanceMetric[];
  statusTone: PerformanceTone;
};

export type PerformanceDistributionItem = {
  bucket: string;
  count: number;
  tone: PerformanceTone;
};

export type PerformanceTrendPoint = {
  date: string;
  throughput: number;
  utilization: number;
  cycleTime: number;
  efficiency: number;
};

export type PerformanceChartPlaceholder = {
  id: string;
  title: string;
  description: string;
};
