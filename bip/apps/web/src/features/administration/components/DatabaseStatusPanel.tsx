import { Badge, Card } from "../../../components/design-system";
import type { DatabaseEntry, ServiceStatus } from "../administration.types";

type DatabaseStatusPanelProps = {
  databases: DatabaseEntry[];
};

const DB_TONE: Record<ServiceStatus, "success" | "warning" | "danger"> = {
  Operational: "success",
  Degraded: "warning",
  Down: "danger"
};

export function DatabaseStatusPanel({ databases }: DatabaseStatusPanelProps) {
  return (
    <Card>
      <div className="administration__section-header">
        <div>
          <p className="administration__kicker">Platform</p>
          <h2>Database Status</h2>
        </div>
        <Badge tone="info">{databases.length} databases</Badge>
      </div>
      <div className="administration__table-scroll">
        <table className="administration__table administration__table--compact">
          <thead>
            <tr>
              <th scope="col">Database</th>
              <th scope="col">Status</th>
              <th scope="col">Latency</th>
              <th scope="col">Connections</th>
              <th scope="col">Last Backup</th>
            </tr>
          </thead>
          <tbody>
            {databases.map((database) => (
              <tr key={database.id}>
                <td className="administration__strong">{database.name}</td>
                <td>
                  <Badge tone={DB_TONE[database.status]}>{database.status}</Badge>
                </td>
                <td>{database.latencyMs}ms</td>
                <td>{database.connections}</td>
                <td>{database.lastBackup}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
