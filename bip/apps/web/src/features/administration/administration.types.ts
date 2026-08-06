export type AdminTone = "neutral" | "success" | "warning" | "danger" | "info";

export type MachineStatus = "Healthy" | "Warning" | "Critical";

export type MachineConnection = "Online" | "Offline" | "Degraded";

export type CollectorStatus = "Running" | "Stalled" | "Stopped";

export type ServiceStatus = "Operational" | "Degraded" | "Down";

export type SchemaStatus = "Up to date" | "Pending" | "Failed";

export type AdminKpi = {
  id: string;
  label: string;
  value: string;
  delta: string;
  deltaTone: AdminTone;
};

export type SystemHealthMetric = {
  id: string;
  label: string;
  value: string;
  status: "Good" | "Warn" | "Bad";
  detail: string;
};

export type ServiceEntry = {
  id: string;
  serviceName: string;
  status: ServiceStatus;
  uptime: string;
  lastRestart: string;
};

export type DatabaseEntry = {
  id: string;
  name: string;
  status: ServiceStatus;
  latencyMs: number;
  connections: number;
  lastBackup: string;
};

export type CollectorEntry = {
  id: string;
  collectorName: string;
  machineId: string;
  status: CollectorStatus;
  version: string;
  lastPulse: string;
  eventsPerMin: number;
  errors: number;
};

export type SchemaVersion = {
  id: string;
  schemaName: string;
  version: number;
  migratedAt: string;
  status: SchemaStatus;
  tables: number;
};

export type MachineRecord = {
  id: string;
  machineId: string;
  machineName: string;
  status: MachineStatus;
  lastSeen: string;
  collectorVersion: string;
  healthScore: number;
  firmware: string;
  connection: MachineConnection;
};

export type AuditEntry = {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  entity: string;
  entityId: string;
  detail: string;
};

export type PlatformInformation = {
  platformName: string;
  version: string;
  environment: string;
  deployDate: string;
  build: string;
  nodes: number;
  storageUsed: string;
  storageTotal: string;
  region: string;
};

export type HealthTimelinePoint = {
  id: string;
  date: string;
  healthScore: number;
  status: MachineStatus;
};

export type AdministrationFilters = {
  search: string;
  status: string;
  connection: string;
  fromDate: string;
  toDate: string;
};

export type AdministrationOptions = {
  statuses: string[];
  connections: string[];
};
