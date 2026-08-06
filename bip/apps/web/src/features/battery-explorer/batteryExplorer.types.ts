export type BatteryExplorerTone = "neutral" | "success" | "warning" | "danger" | "info";

export type BatteryRecord = {
  id: string;
  serialNumber: string;
  ringMac: string;
  ringName: string;
  product: string;
  machine: string;
  slot: string;
  currentState: string;
  firmware: string;
  firstSeen: string;
  lastSeen: string;
  lifecycleStatus: string;
  tone: BatteryExplorerTone;
};

export type BatteryExplorerFilters = {
  serialNumberQuery: string;
  ringMacQuery: string;
  ringNameQuery: string;
  product: string;
  machine: string;
  slot: string;
  state: string;
  firmware: string;
  dateFrom: string;
  dateTo: string;
};

export type ExplorerOptions = {
  products: string[];
  machines: string[];
  slots: string[];
  states: string[];
  firmwares: string[];
};

export type ExplorerSortColumn =
  | "serialNumber"
  | "ringName"
  | "product"
  | "machine"
  | "currentState"
  | "firmware"
  | "firstSeen"
  | "lastSeen";

export type ExplorerSort = {
  column: ExplorerSortColumn;
  direction: "asc" | "desc";
};

export type LifecycleStageDetail = {
  id: string;
  name: string;
  reached: boolean;
  current: boolean;
  note: string;
};

export type BatteryDetailEvent = {
  id: string;
  event: string;
  context: string;
  timestamp: string;
};

export type DecisionSummary = {
  recommendation: string;
  confidence: string;
  note: string;
};

export type ChartPlaceholderItem = {
  id: string;
  title: string;
  description: string;
};

export type BatteryDetail = {
  record: BatteryRecord;
  lifecycle: LifecycleStageDetail[];
  recentEvents: BatteryDetailEvent[];
  decisionSummary: DecisionSummary;
  charts: ChartPlaceholderItem[];
};
