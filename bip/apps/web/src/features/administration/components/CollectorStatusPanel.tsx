import { Badge, Card } from "../../../components/design-system";
import { getCollectorTone } from "../administration.mock";
import type { CollectorEntry } from "../administration.types";

type CollectorStatusPanelProps = {
  collectors: CollectorEntry[];
};

export function CollectorStatusPanel({ collectors }: CollectorStatusPanelProps) {
  return (
    <Card>
      <div className="administration__section-header">
        <div>
          <p className="administration__kicker">Collectors</p>
          <h2>Collector Status</h2>
        </div>
        <Badge tone="info">{collectors.length} collectors</Badge>
      </div>
      <div className="administration__table-scroll">
        <table className="administration__table administration__table--compact">
          <thead>
            <tr>
              <th scope="col">Collector</th>
              <th scope="col">Status</th>
              <th scope="col">Version</th>
              <th scope="col">Events/min</th>
              <th scope="col">Errors</th>
            </tr>
          </thead>
          <tbody>
            {collectors.map((collector) => (
              <tr key={collector.id}>
                <td className="administration__strong">{collector.collectorName}</td>
                <td>
                  <Badge tone={getCollectorTone(collector.status)}>{collector.status}</Badge>
                </td>
                <td>{collector.version}</td>
                <td>{collector.eventsPerMin}</td>
                <td>{collector.errors}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
