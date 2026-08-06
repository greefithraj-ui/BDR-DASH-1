import { Badge, Card } from "../../../components/design-system";
import type { HealthTimelinePoint, MachineStatus } from "../administration.types";

type HealthMetricsPanelProps = {
  points: HealthTimelinePoint[];
};

const STATUS_TONE: Record<MachineStatus, "success" | "warning" | "danger"> = {
  Healthy: "success",
  Warning: "warning",
  Critical: "danger"
};

export function HealthMetricsPanel({ points }: HealthMetricsPanelProps) {
  return (
    <Card>
      <div className="administration__section-header">
        <div>
          <p className="administration__kicker">Metrics</p>
          <h2>Health Timeline</h2>
        </div>
        <Badge tone="info">{points.length} days</Badge>
      </div>
      <div className="administration__table-scroll">
        <table className="administration__table administration__table--compact">
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Health Score</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {points.map((point) => (
              <tr key={point.id}>
                <td>{point.date}</td>
                <td className="administration__strong">{point.healthScore}</td>
                <td>
                  <Badge tone={STATUS_TONE[point.status]}>{point.status}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
