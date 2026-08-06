export type MachineTone = "neutral" | "success" | "warning" | "danger" | "info";

export type MachineStatus = "Online" | "Offline";

export type MachineFirmwareSummary = {
  firmware: string;
  count: number;
};

export type MachineProductDistribution = {
  product: string;
  count: number;
};

export type MachineRecord = {
  id: string;
  machineId: string;
  name: string;
  status: MachineStatus;
  slotCount: number;
  activeBatteries: number;
  pendingRemovalCount: number;
  finalizedCount: number;
  healthScore: number;
  lastSeen: string;
  dominantFirmware: string;
  slotsOccupied: number;
  firmwareSummary: MachineFirmwareSummary[];
  productDistribution: MachineProductDistribution[];
  batteryCount: number;
};

export type MachineExplorerFilters = {
  query: string;
  status: string;
};

export type MachineExplorerOptions = {
  statuses: MachineStatus[];
};

export type MachineExplorerSortColumn = "machineId" | "healthScore" | "activeBatteries" | "lastSeen";

export type MachineExplorerSort = {
  column: MachineExplorerSortColumn;
  direction: "asc" | "desc";
};

export type SlotOccupancySlot = {
  slot: string;
  occupied: boolean;
  serialNumber?: string;
  currentState?: string;
  tone?: MachineTone;
};

export type MachineBatterySummary = {
  id: string;
  serialNumber: string;
  slot: string;
  currentState: string;
  firmware: string;
  lastSeen: string;
  tone: MachineTone;
};

export type MachineDetailEvent = {
  id: string;
  event: string;
  context: string;
  timestamp: string;
};

export type MachineTimelineStage = {
  id: string;
  name: string;
  reached: boolean;
  current: boolean;
  note: string;
};

export type MachineChartPlaceholder = {
  id: string;
  title: string;
  description: string;
};

export type HealthFactor = {
  label: string;
  value: string;
  tone: MachineTone;
};

export type MachineDetail = {
  record: MachineRecord;
  slotOverview: SlotOccupancySlot[];
  batteryList: MachineBatterySummary[];
  recentEvents: MachineDetailEvent[];
  timeline: MachineTimelineStage[];
  charts: MachineChartPlaceholder[];
  healthFactors: HealthFactor[];
};
