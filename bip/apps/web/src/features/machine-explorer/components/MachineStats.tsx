import { Badge, Card, MetricCard } from "../../../components/design-system";
import type { MachineDetail } from "../machineExplorer.types";

type MachineStatsProps = {
  detail: MachineDetail;
};

export function MachineStats({ detail }: MachineStatsProps) {
  const { record } = detail;
  const scoreTone = record.healthScore >= 80 ? "success" : record.healthScore >= 60 ? "info" : "danger";

  return (
    <Card>
      <div className="machine-explorer-detail__section-header">
        <div>
          <p className="machine-explorer-detail__kicker">Performance</p>
          <h2>Current Statistics</h2>
        </div>
        <Badge tone="info">Live Data</Badge>
      </div>
      <div className="machine-explorer-detail__metric-grid">
        <MetricCard label="Active Batteries" value={String(record.activeBatteries)} />
        <MetricCard label="Pending Removal" value={String(record.pendingRemovalCount)} tone={record.pendingRemovalCount > 0 ? "warning" : "neutral"} />
        <MetricCard label="Finalized" value={String(record.finalizedCount)} />
        <MetricCard label="Health Score" value={`${record.healthScore}/100`} tone={scoreTone} />
        <MetricCard label="Slots Occupied" value={`${record.slotsOccupied}/${record.slotCount}`} />
        <MetricCard label="Batteries Present" value={String(record.batteryCount)} />
      </div>
    </Card>
  );
}
