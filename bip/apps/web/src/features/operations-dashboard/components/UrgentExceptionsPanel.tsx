import { Link } from "react-router-dom";
import { Badge, Card } from "../../../components/design-system";
import type { UrgentException } from "../useOperationsDashboard";

type UrgentExceptionsPanelProps = {
  exceptions: UrgentException[];
};

export function UrgentExceptionsPanel({ exceptions }: UrgentExceptionsPanelProps) {
  return (
    <Card className="ops-exceptions-card">
      <div className="ops-panel-header">
        <h2>URGENT EXCEPTIONS & AGING RINGS</h2>
        <Badge tone="danger">{exceptions.length} ACTIONABLE ALERTS</Badge>
      </div>

      <div className="ops-exceptions-list">
        {exceptions.length === 0 ? (
          <p className="ops-empty-text">No urgent exceptions detected. All operations normal.</p>
        ) : (
          exceptions.map((ex) => (
            <div key={ex.id} className={`ops-exception-item ops-exception-item--${ex.severity}`}>
              <div className="ops-exception-header">
                <span className="ops-exception-title">
                  {ex.severity === "danger" ? "🔴" : "🟡"} {ex.ringId}: {ex.type}
                </span>
                <Badge tone={ex.severity}>{ex.elapsedTime}</Badge>
              </div>

              <p className="ops-exception-reason">{ex.reason}</p>

              <div className="ops-exception-footer">
                <span className="ops-exception-meta">Station: {ex.machineId}</span>
                <Link
                  to={`/battery-explorer?ringId=${encodeURIComponent(ex.ringId)}`}
                  className="ops-action-link"
                >
                  View Ring Detail ➔
                </Link>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
