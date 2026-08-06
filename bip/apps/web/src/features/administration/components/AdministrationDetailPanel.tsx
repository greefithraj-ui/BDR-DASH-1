import { Badge, Card, ChartContainer, MetricCard } from "../../../components/design-system";
import { getConnectionTone, getMachineTone } from "../administration.mock";
import type { AuditEntry, HealthTimelinePoint, MachineRecord } from "../administration.types";
import { AuditLogPanel } from "./AuditLogPanel";
import { HealthMetricsPanel } from "./HealthMetricsPanel";

type AdministrationDetailPanelProps = {
  machine: MachineRecord;
  onBack: () => void;
  points: HealthTimelinePoint[];
  auditEntries: AuditEntry[];
};

export function AdministrationDetailPanel({ machine, onBack, points, auditEntries }: AdministrationDetailPanelProps) {
  return (
    <section className="administration-detail" aria-labelledby="administration-detail-title">
      <header className="administration-detail__hero">
        <div>
          <button className="administration__button" type="button" onClick={onBack}>
            ← Back to administration
          </button>
          <p className="administration__kicker">Machine Details</p>
          <h1 id="administration-detail-title">{machine.machineId}</h1>
          <p className="administration-detail__subtitle">{machine.machineName}</p>
        </div>
        <div className="administration-detail__badges">
          <Badge tone={getMachineTone(machine)}>{machine.status}</Badge>
          <Badge tone={getConnectionTone(machine)}>{machine.connection}</Badge>
          <Badge tone="neutral">{machine.firmware}</Badge>
        </div>
      </header>

      <Card>
        <div className="administration__section-header">
          <div>
            <p className="administration__kicker">Registry</p>
            <h2>Machine Details</h2>
          </div>
          <Badge tone="info">Mock Data</Badge>
        </div>
        <div className="administration-detail__metric-grid">
          <MetricCard label="Machine ID" value={machine.machineId} />
          <MetricCard label="Machine Name" value={machine.machineName} />
          <MetricCard label="Status" value={machine.status} />
          <MetricCard label="Last Seen" value={machine.lastSeen} />
          <MetricCard label="Collector Version" value={machine.collectorVersion} />
          <MetricCard label="Health Score" value={String(machine.healthScore)} />
          <MetricCard label="Firmware" value={machine.firmware} />
          <MetricCard label="Connection" value={machine.connection} />
        </div>
      </Card>

      <div className="administration-detail__grid">
        <HealthMetricsPanel points={points} />
        <AuditLogPanel entries={auditEntries} />
      </div>

      <div className="administration-detail__summary">
        <Card>
          <div className="administration__section-header">
            <div>
              <p className="administration__kicker">Summary</p>
              <h2>Status Summary</h2>
            </div>
            <Badge tone={getMachineTone(machine)}>{machine.status}</Badge>
          </div>
          <dl className="administration-detail__summary-list">
            <div>
              <dt>Connection</dt>
              <dd>{machine.connection}</dd>
            </div>
            <div>
              <dt>Health Score</dt>
              <dd>{machine.healthScore} / 100</dd>
            </div>
            <div>
              <dt>Audit Entries</dt>
              <dd>{auditEntries.length}</dd>
            </div>
            <div>
              <dt>Timeline Points</dt>
              <dd>{points.length}</dd>
            </div>
          </dl>
        </Card>
      </div>

      <section className="administration-detail__charts" aria-label="Machine placeholder charts">
        <div className="administration__section-header">
          <div>
            <p className="administration__kicker">Charts</p>
            <h2>Placeholder Charts</h2>
          </div>
          <Badge tone="info">ChartContainer only</Badge>
        </div>
        <div className="administration-detail__chart-grid">
          <ChartContainer title="Health Score Trend" description="Placeholder chart container for machine health score over the last 14 days." />
          <ChartContainer title="Uptime Distribution" description="Placeholder chart container for machine uptime and connection stability." />
        </div>
      </section>
    </section>
  );
}
