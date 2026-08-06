import { Badge, Card } from "../../../components/design-system";
import type { SystemHealthMetric } from "../administration.types";

type SystemHealthPanelProps = {
  metrics: SystemHealthMetric[];
};

const METRIC_TONE: Record<SystemHealthMetric["status"], "success" | "warning" | "danger"> = {
  Good: "success",
  Warn: "warning",
  Bad: "danger"
};

export function SystemHealthPanel({ metrics }: SystemHealthPanelProps) {
  return (
    <Card>
      <div className="administration__section-header">
        <div>
          <p className="administration__kicker">Infrastructure</p>
          <h2>System Health</h2>
        </div>
        <Badge tone="info">Live mock</Badge>
      </div>
      <div className="administration__metric-grid">
        {metrics.map((metric) => (
          <div key={metric.id} className="administration__metric-card">
            <div className="administration__metric-head">
              <span className="administration__metric-label">{metric.label}</span>
              <Badge tone={METRIC_TONE[metric.status]}>{metric.status}</Badge>
            </div>
            <strong className="administration__metric-value">{metric.value}</strong>
            <span className="administration__metric-detail">{metric.detail}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
