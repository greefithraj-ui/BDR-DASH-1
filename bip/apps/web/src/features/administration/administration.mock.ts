import type {
  AdminKpi,
  AuditEntry,
  CollectorEntry,
  CollectorStatus,
  DatabaseEntry,
  HealthTimelinePoint,
  MachineConnection,
  MachineRecord,
  MachineStatus,
  PlatformInformation,
  SchemaVersion,
  SchemaStatus,
  ServiceEntry,
  SystemHealthMetric
} from "./administration.types";

const STATUS_TONE: Record<MachineStatus, "success" | "warning" | "danger"> = {
  Healthy: "success",
  Warning: "warning",
  Critical: "danger"
};

const CONNECTION_TONE: Record<MachineConnection, "success" | "danger" | "warning"> = {
  Online: "success",
  Offline: "danger",
  Degraded: "warning"
};

const COLLECTOR_TONE: Record<CollectorStatus, "success" | "warning" | "danger"> = {
  Running: "success",
  Stalled: "warning",
  Stopped: "danger"
};

const SCHEMA_TONE: Record<SchemaStatus, "success" | "warning" | "danger"> = {
  "Up to date": "success",
  Pending: "warning",
  Failed: "danger"
};

const MACHINES: MachineRecord[] = [
  { id: "m-01", machineId: "AQC-01", machineName: "AQC-01 · Line 1", status: "Healthy", lastSeen: "2026-08-02 07:58", collectorVersion: "3.1.2", healthScore: 96, firmware: "v3.0.2", connection: "Online" },
  { id: "m-02", machineId: "AQC-02", machineName: "AQC-02 · Line 2", status: "Warning", lastSeen: "2026-08-02 07:57", collectorVersion: "3.1.2", healthScore: 84, firmware: "v3.0.2", connection: "Online" },
  { id: "m-03", machineId: "AQC-03", machineName: "AQC-03 · Line 3", status: "Healthy", lastSeen: "2026-08-02 07:58", collectorVersion: "3.1.2", healthScore: 93, firmware: "v2.4.1", connection: "Online" },
  { id: "m-04", machineId: "AQC-04", machineName: "AQC-04 · Line 4", status: "Warning", lastSeen: "2026-08-02 07:41", collectorVersion: "3.0.9", healthScore: 71, firmware: "v2.4.1", connection: "Degraded" },
  { id: "m-05", machineId: "AQC-05", machineName: "AQC-05 · Line 5", status: "Healthy", lastSeen: "2026-08-02 07:58", collectorVersion: "3.1.2", healthScore: 91, firmware: "v2.3.8", connection: "Online" },
  { id: "m-06", machineId: "AQC-06", machineName: "AQC-06 · Line 6", status: "Healthy", lastSeen: "2026-08-02 07:57", collectorVersion: "3.1.1", healthScore: 89, firmware: "v1.9.0", connection: "Online" },
  { id: "m-07", machineId: "AQC-07", machineName: "AQC-07 · Line 7", status: "Warning", lastSeen: "2026-08-02 07:52", collectorVersion: "3.1.0", healthScore: 78, firmware: "v1.9.0", connection: "Online" },
  { id: "m-08", machineId: "AQC-08", machineName: "AQC-08 · Line 8", status: "Critical", lastSeen: "2026-08-01 22:14", collectorVersion: "3.0.5", healthScore: 43, firmware: "v2.3.8", connection: "Offline" }
];

function buildCollectors(): CollectorEntry[] {
  const statusByMachine: Record<string, CollectorStatus> = {
    "AQC-01": "Running",
    "AQC-02": "Running",
    "AQC-03": "Running",
    "AQC-04": "Stalled",
    "AQC-05": "Running",
    "AQC-06": "Running",
    "AQC-07": "Running",
    "AQC-08": "Stopped"
  };

  return MACHINES.map((machine, index) => ({
    id: `collector-${machine.machineId}`,
    collectorName: `Collector · ${machine.machineId}`,
    machineId: machine.machineId,
    status: statusByMachine[machine.machineId] ?? "Running",
    version: machine.collectorVersion,
    lastPulse: machine.lastSeen,
    eventsPerMin: 60 + ((index * 37) % 140),
    errors: machine.machineId === "AQC-08" ? 12 : machine.machineId === "AQC-04" ? 3 : (index * 11) % 3
  }));
}

function buildSchemas(): SchemaVersion[] {
  return [
    { id: "schema-core", schemaName: "core.schema", version: 42, migratedAt: "2026-08-01 03:00", status: "Up to date", tables: 64 },
    { id: "schema-fleet", schemaName: "fleet.schema", version: 19, migratedAt: "2026-07-30 02:30", status: "Up to date", tables: 28 },
    { id: "schema-quality", schemaName: "quality.schema", version: 11, migratedAt: "2026-07-28 04:00", status: "Up to date", tables: 17 },
    { id: "schema-performance", schemaName: "performance.schema", version: 24, migratedAt: "2026-07-31 05:00", status: "Up to date", tables: 12 },
    { id: "schema-insights", schemaName: "insights.schema", version: 8, migratedAt: "2026-08-02 06:00", status: "Failed", tables: 9 }
  ];
}

function buildServices(): ServiceEntry[] {
  return [
    { id: "svc-auth", serviceName: "auth-service", status: "Operational", uptime: "99.99%", lastRestart: "2026-07-01 02:00" },
    { id: "svc-ingestion", serviceName: "ingestion-service", status: "Degraded", uptime: "98.2%", lastRestart: "2026-08-02 04:12" },
    { id: "svc-event-bus", serviceName: "event-bus", status: "Operational", uptime: "99.8%", lastRestart: "2026-06-30 02:00" },
    { id: "svc-reports", serviceName: "reports-engine", status: "Operational", uptime: "99.6%", lastRestart: "2026-07-02 02:00" },
    { id: "svc-notifications", serviceName: "notification-service", status: "Operational", uptime: "99.9%", lastRestart: "2026-07-05 02:00" }
  ];
}

function buildDatabases(): DatabaseEntry[] {
  return [
    { id: "db-core", name: "bip_core", status: "Operational", latencyMs: 8, connections: 42, lastBackup: "2026-08-02 02:00" },
    { id: "db-fleet", name: "bip_fleet", status: "Operational", latencyMs: 12, connections: 31, lastBackup: "2026-08-02 02:05" },
    { id: "db-quality", name: "bip_quality", status: "Degraded", latencyMs: 34, connections: 12, lastBackup: "2026-08-01 02:00" }
  ];
}

function buildHealthMetrics(): SystemHealthMetric[] {
  return [
    { id: "health-cpu", label: "CPU", value: "42%", status: "Good", detail: "Within budget" },
    { id: "health-memory", label: "Memory", value: "61%", status: "Good", detail: "8.5 GB of 14 GB" },
    { id: "health-storage", label: "Storage", value: "78%", status: "Good", detail: "18.4 TB of 32 TB" },
    { id: "health-queue", label: "Event Queue", value: "128", status: "Good", detail: "1.9k events/min" },
    { id: "health-errors", label: "Error Rate", value: "0.9%", status: "Good", detail: "Below 2% threshold" },
    { id: "health-uptime", label: "Uptime", value: "99.97%", status: "Good", detail: "Last 90 days" }
  ];
}

function buildAuditEntries(): AuditEntry[] {
  const entries: AuditEntry[] = [
    { id: "audit-0001", timestamp: "2026-08-02 07:44", actor: "admin@bip.local", action: "Alert", entity: "Machine", entityId: "AQC-04", detail: "Collector stall detected on AQC-04; 3 events dropped" },
    { id: "audit-0002", timestamp: "2026-08-02 07:31", actor: "ops@bip.local", action: "Restart", entity: "Machine", entityId: "AQC-07", detail: "Collector service restarted after calibration drift alert" },
    { id: "audit-0003", timestamp: "2026-08-02 06:00", actor: "deploy@bip.local", action: "Migrate", entity: "Schema", entityId: "insights.schema", detail: "Migration v8 failed; retry scheduled" },
    { id: "audit-0004", timestamp: "2026-08-02 05:18", actor: "admin@bip.local", action: "Configure", entity: "Machine", entityId: "AQC-06", detail: "Firmware v1.9.0 confirmed on all lines" },
    { id: "audit-0005", timestamp: "2026-08-02 04:12", actor: "deploy@bip.local", action: "Restart", entity: "Service", entityId: "ingestion-service", detail: "Restarted after degraded latency; backfill in progress" },
    { id: "audit-0006", timestamp: "2026-08-02 03:00", actor: "deploy@bip.local", action: "Migrate", entity: "Schema", entityId: "core.schema", detail: "Migration v42 applied successfully" },
    { id: "audit-0007", timestamp: "2026-08-02 02:00", actor: "ops@bip.local", action: "Backup", entity: "Database", entityId: "bip_core", detail: "Nightly backup completed" },
    { id: "audit-0008", timestamp: "2026-08-02 01:40", actor: "admin@bip.local", action: "Login", entity: "User", entityId: "admin", detail: "Session started from ops console" },
    { id: "audit-0009", timestamp: "2026-08-01 22:14", actor: "system", action: "Alert", entity: "Machine", entityId: "AQC-08", detail: "Connection lost; machine marked offline" },
    { id: "audit-0010", timestamp: "2026-08-01 21:30", actor: "ops@bip.local", action: "Configure", entity: "Machine", entityId: "AQC-08", detail: "Collector v3.0.5 settings applied before outage" },
    { id: "audit-0011", timestamp: "2026-08-01 15:22", actor: "admin@bip.local", action: "Export", entity: "Report", entityId: "weekly-exec", detail: "Weekly executive report exported to ops board" },
    { id: "audit-0012", timestamp: "2026-08-01 08:10", actor: "ops@bip.local", action: "Update", entity: "Machine", entityId: "AQC-02", detail: "Contact anomaly flag set on AQC-02 for investigation" }
  ];

  for (let index = 0; index < MACHINES.length; index += 1) {
    const machine = MACHINES[index];
    const daysBack = 2 + (index % 2);
    entries.push({
      id: `audit-machine-${machine.machineId}`,
      timestamp: `2026-08-0${2 - daysBack} 0${(index % 8) + 1}:20`,
      actor: "admin@bip.local",
      action: "Configure",
      entity: "Machine",
      entityId: machine.machineId,
      detail: `Collector v${machine.collectorVersion} configuration acknowledged`
    });
  }

  return entries.sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1));
}

function buildPlatform(): PlatformInformation {
  return {
    platformName: "Battery Intelligence Platform",
    version: "12.0.0",
    environment: "Production",
    deployDate: "2026-08-01",
    build: "2026.08.01.042",
    nodes: 3,
    storageUsed: "18.4 TB",
    storageTotal: "32 TB",
    region: "eu-central"
  };
}

function buildKpis(machines: MachineRecord[], collectors: CollectorEntry[], schemas: SchemaVersion[]): AdminKpi[] {
  const healthy = machines.filter((machine) => machine.status === "Healthy").length;
  const offline = machines.filter((machine) => machine.connection === "Offline").length;
  const running = collectors.filter((collector) => collector.status === "Running").length;
  const schemaVersion = Math.max(...schemas.map((schema) => schema.version));

  return [
    { id: "admin-kpi-healthy", label: "Healthy Machines", value: `${healthy} / ${machines.length}`, delta: "4 online now", deltaTone: "success" },
    { id: "admin-kpi-offline", label: "Offline Machines", value: String(offline), delta: "-1 this week", deltaTone: "warning" },
    { id: "admin-kpi-collectors", label: "Collector Status", value: `${running} / ${collectors.length} running`, delta: "1 stalled · 1 stopped", deltaTone: "info" },
    { id: "admin-kpi-schema", label: "Schema Version", value: String(schemaVersion), delta: "1 migration pending", deltaTone: "success" },
    { id: "admin-kpi-health", label: "Platform Health", value: "98%", delta: "+0.4 pts", deltaTone: "success" }
  ];
}

function shiftDate(dateStr: string, daysBack: number): string {
  const [year, month, day] = dateStr.split("-").map(Number);
  const date = new Date(year, month - 1, day - daysBack);
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function statusFromScore(score: number): MachineStatus {
  if (score >= 85) return "Healthy";
  if (score >= 70) return "Warning";
  return "Critical";
}

function buildTimeline(machine: MachineRecord): HealthTimelinePoint[] {
  const points: HealthTimelinePoint[] = [];

  for (let n = 13; n >= 0; n -= 1) {
    const variation = ((machine.healthScore + n * 11) % 15) - 7;
    const score = Math.max(20, Math.min(99, machine.healthScore + variation));
    points.push({
      id: `${machine.machineId}-tl-${n}`,
      date: shiftDate("2026-08-02", n),
      healthScore: score,
      status: statusFromScore(score)
    });
  }

  return points;
}

export function getMachineTone(machine: MachineRecord): "success" | "warning" | "danger" {
  return STATUS_TONE[machine.status];
}

export function getConnectionTone(machine: MachineRecord): "success" | "warning" | "danger" {
  return CONNECTION_TONE[machine.connection];
}

export function getCollectorTone(status: CollectorStatus): "success" | "warning" | "danger" {
  return COLLECTOR_TONE[status];
}

export function getSchemaTone(status: SchemaStatus): "success" | "warning" | "danger" {
  return SCHEMA_TONE[status];
}

export function getHealthTimeline(machineId: string): HealthTimelinePoint[] {
  const machine = MACHINES.find((item) => item.machineId === machineId) ?? MACHINES[0];
  return buildTimeline(machine);
}

const mockAdministration = {
  machines: MACHINES,
  collectors: buildCollectors(),
  schemas: buildSchemas(),
  services: buildServices(),
  databases: buildDatabases(),
  healthMetrics: buildHealthMetrics(),
  auditEntries: buildAuditEntries(),
  platform: buildPlatform()
};

export function getMockAdministration() {
  return {
    machines: mockAdministration.machines,
    collectors: mockAdministration.collectors,
    schemas: mockAdministration.schemas,
    services: mockAdministration.services,
    databases: mockAdministration.databases,
    healthMetrics: mockAdministration.healthMetrics,
    auditEntries: mockAdministration.auditEntries,
    platform: mockAdministration.platform,
    kpis: buildKpis(mockAdministration.machines, mockAdministration.collectors, mockAdministration.schemas)
  };
}
