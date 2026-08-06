import { Badge, Card, MetricCard } from "../../../components/design-system";
import type { BatteryDetail } from "../batteryExplorer.types";

type DetailCurrentContextProps = {
  detail: BatteryDetail;
};

export function DetailCurrentContext({ detail }: DetailCurrentContextProps) {
  const { record } = detail;

  return (
    <Card>
      <div className="battery-explorer-detail__section-header">
        <div>
          <p className="battery-explorer-detail__kicker">Context</p>
          <h2>Current Machine & Slot</h2>
        </div>
        <Badge tone={record.tone}>{record.currentState}</Badge>
      </div>
      <div className="battery-explorer-detail__metric-grid">
        <MetricCard label="Current Machine" value={record.machine} />
        <MetricCard label="Current Slot" value={record.slot} />
        <MetricCard label="Current State" value={record.currentState} tone={record.tone} />
        <MetricCard label="First Seen" value={record.firstSeen} />
        <MetricCard label="Last Seen" value={record.lastSeen} />
        <MetricCard label="Ring" value={record.ringName} />
      </div>
    </Card>
  );
}
