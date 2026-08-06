import { Badge, Card } from "../../../components/design-system";
import type { Alert } from "../analyticsHub.types";

type AlertsPanelProps = {
  alerts: Alert[];
};

export function AlertsPanel({ alerts }: AlertsPanelProps) {
  return (
    <Card>
      <div className="analytics-hub__section-header">
        <div>
          <p className="analytics-hub__kicker">Attention</p>
          <h2>Top Alerts</h2>
        </div>
        <Badge tone="warning">6 open</Badge>
      </div>
      <div className="analytics-hub__alert-list">
        {alerts.map((alert) => (
          <article key={alert.id} className="analytics-hub__alert">
            <Badge tone={alert.severity}>{alert.severity}</Badge>
            <div>
              <h3>{alert.title}</h3>
              <p>{alert.detail}</p>
              <time>{alert.timestamp}</time>
            </div>
          </article>
        ))}
      </div>
    </Card>
  );
}
