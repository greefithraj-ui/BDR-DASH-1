export type BatteryDashboardTone = "neutral" | "success" | "warning" | "danger" | "info";

export type BatteryStatusMetric = {
  id: string;
  label: string;
  value: string;
  helper: string;
  tone: BatteryDashboardTone;
};

export type MachineHealthItem = {
  id: string;
  machine: string;
  status: string;
  detail: string;
  tone: BatteryDashboardTone;
};

export type RingStateItem = {
  id: string;
  state: string;
  value: string;
  tone: BatteryDashboardTone;
};

export type ActiveMachineItem = {
  id: string;
  name: string;
  currentRing: string;
  operatorState: string;
  tone: BatteryDashboardTone;
};

export type LifecycleStage = {
  id: string;
  stage: string;
  count: string;
  description: string;
};

export type CollectorStatusItem = {
  id: string;
  label: string;
  value: string;
  tone: BatteryDashboardTone;
};

export type PendingRemovalItem = {
  id: string;
  batteryId: string;
  ring: string;
  reason: string;
  age: string;
  tone: BatteryDashboardTone;
};

export type BatteryEventItem = {
  id: string;
  event: string;
  batteryId: string;
  context: string;
  timestamp: string;
};

export type SystemHealthItem = {
  id: string;
  label: string;
  value: string;
  tone: BatteryDashboardTone;
};

export type ChartPlaceholderItem = {
  id: string;
  title: string;
  description: string;
};

export type BatteryIntelligenceDashboardData = {
  statusMetrics: BatteryStatusMetric[];
  machineHealth: MachineHealthItem[];
  ringStates: RingStateItem[];
  activeMachines: ActiveMachineItem[];
  lifecycle: LifecycleStage[];
  collectorStatus: CollectorStatusItem[];
  pendingRemovals: PendingRemovalItem[];
  recentEvents: BatteryEventItem[];
  systemHealth: SystemHealthItem[];
  charts: ChartPlaceholderItem[];
};
