export type ProductTone = "neutral" | "success" | "warning" | "danger" | "info";

export type ProductFirmwareSummary = {
  firmware: string;
  count: number;
};

export type ProductLifecycleDistribution = {
  stage: string;
  count: number;
};

export type ProductRecord = {
  id: string;
  product: string;
  category: string;
  description: string;
  totalBatteries: number;
  activeBatteries: number;
  pendingRemoval: number;
  finalized: number;
  failed: number;
  passRate: number;
  healthScore: number;
  avgCycle: string;
  status: string;
  statusTone: ProductTone;
  machines: string[];
  lastUpdated: string;
  firmwareSummary: ProductFirmwareSummary[];
  lifecycleDistribution: ProductLifecycleDistribution[];
};

export type ProductFilters = {
  product: string;
  firmware: string;
  machine: string;
  lifecycleState: string;
  dateFrom: string;
  dateTo: string;
  search: string;
};

export type ProductOptions = {
  products: string[];
  firmwares: string[];
  machines: string[];
  lifecycleStates: string[];
};

export type ProductKpi = {
  id: string;
  label: string;
  value: string;
  delta: string;
  deltaTone: ProductTone;
};

export type ProductMetric = {
  label: string;
  value: string;
  tone?: ProductTone;
};

export type ProductComparisonCard = {
  id: string;
  product: string;
  comparison: string;
  metrics: ProductMetric[];
  statusTone: ProductTone;
};

export type ProductDistributionItem = {
  product: string;
  count: number;
  share: number;
};

export type FailureDistributionItem = {
  cause: string;
  count: number;
  tone: ProductTone;
};

export type FleetLifecycleItem = {
  stage: string;
  count: number;
  tone: ProductTone;
};

export type ProductChartPlaceholder = {
  id: string;
  title: string;
  description: string;
};
