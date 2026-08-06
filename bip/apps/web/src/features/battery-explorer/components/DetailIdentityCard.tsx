import { Badge, Card, MetricCard } from "../../../components/design-system";
import type { BatteryDetail } from "../batteryExplorer.types";

type DetailIdentityCardProps = {
  detail: BatteryDetail;
};

export function DetailIdentityCard({ detail }: DetailIdentityCardProps) {
  const { record } = detail;

  return (
    <Card>
      <div className="battery-explorer-detail__section-header">
        <div>
          <p className="battery-explorer-detail__kicker">Identity</p>
          <h2>Identity Card</h2>
        </div>
        <Badge tone="info">Live Data</Badge>
      </div>
      <div className="battery-explorer-detail__metric-grid">
        <MetricCard label="Serial Number" value={record.serialNumber} />
        <MetricCard label="Product" value={record.product} />
        <MetricCard label="Firmware" value={record.firmware} />
        <MetricCard label="Ring Name" value={record.ringName} />
        <MetricCard label="Ring MAC" value={record.ringMac} />
        <MetricCard label="Lifecycle Status" value={record.lifecycleStatus} tone={record.tone} />
      </div>
    </Card>
  );
}
