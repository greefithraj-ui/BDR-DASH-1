import { Card, MetricCard } from "../../../components/design-system";
import type { MachineDetail } from "../machineExplorer.types";
import { StatusIndicator } from "./MachineCard";

type MachineInfoCardProps = {
  detail: MachineDetail;
};

export function MachineInfoCard({ detail }: MachineInfoCardProps) {
  const { record } = detail;

  return (
    <Card>
      <div className="machine-explorer-detail__section-header">
        <div>
          <p className="machine-explorer-detail__kicker">Machine</p>
          <h2>Machine Information</h2>
        </div>
        <StatusIndicator status={record.status} />
      </div>
      <div className="machine-explorer-detail__metric-grid">
        <MetricCard label="Machine ID" value={record.machineId} />
        <MetricCard label="Name" value={record.name} />
        <MetricCard label="Status" value={record.status} tone={record.status === "Online" ? "success" : "danger"} />
        <MetricCard label="Slot Capacity" value={String(record.slotCount)} />
        <MetricCard label="Dominant Firmware" value={record.dominantFirmware} />
        <MetricCard label="Last Seen" value={record.lastSeen} />
      </div>
    </Card>
  );
}
