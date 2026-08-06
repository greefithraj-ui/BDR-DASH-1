import { Badge, Card } from "../../../components/design-system";
import type { AuditEntry } from "../administration.types";

type AuditLogPanelProps = {
  entries: AuditEntry[];
};

export function AuditLogPanel({ entries }: AuditLogPanelProps) {
  return (
    <Card>
      <div className="administration__section-header">
        <div>
          <p className="administration__kicker">Audit</p>
          <h2>Audit Log</h2>
        </div>
        <Badge tone="neutral">{entries.length} entries</Badge>
      </div>
      <div className="administration__table-scroll">
        <table className="administration__table">
          <thead>
            <tr>
              <th scope="col">Timestamp</th>
              <th scope="col">Actor</th>
              <th scope="col">Action</th>
              <th scope="col">Entity</th>
              <th scope="col">Entity ID</th>
              <th scope="col">Detail</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.id}>
                <td>{entry.timestamp}</td>
                <td>{entry.actor}</td>
                <td className="administration__strong">{entry.action}</td>
                <td>{entry.entity}</td>
                <td>{entry.entityId}</td>
                <td>{entry.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
