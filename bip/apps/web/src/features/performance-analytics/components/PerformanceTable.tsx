import { Badge, Card } from "../../../components/design-system";
import type { PerformanceRecord } from "../performanceAnalytics.types";

type PerformanceTableProps = {
  records: PerformanceRecord[];
  onSelect: (record: PerformanceRecord) => void;
};

export function PerformanceTable({ records, onSelect }: PerformanceTableProps) {
  return (
    <Card>
      <div className="performance-analytics__section-header">
        <div>
          <p className="performance-analytics__kicker">Records</p>
          <h2>Performance Table</h2>
        </div>
        <Badge tone="info">{records.length} records</Badge>
      </div>
      <div className="performance-analytics__table-scroll">
        <table className="performance-analytics__table">
          <thead>
            <tr>
              <th scope="col">Machine</th>
              <th scope="col">Product</th>
              <th scope="col">Firmware</th>
              <th scope="col">Date</th>
              <th scope="col">Produced</th>
              <th scope="col">Throughput</th>
              <th scope="col">Cycle Time</th>
              <th scope="col">Utilization</th>
              <th scope="col">Processing Rate</th>
              <th scope="col">Efficiency</th>
              <th scope="col">Performance Score</th>
              <th scope="col">Status</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.id} className="performance-analytics__row" onClick={() => onSelect(record)}>
                <td className="performance-analytics__strong">{record.machine}</td>
                <td>{record.product}</td>
                <td>{record.firmware}</td>
                <td>{record.date}</td>
                <td>{record.produced}</td>
                <td>{record.throughput}/hr</td>
                <td>{record.cycleTime}s</td>
                <td>{record.utilization}%</td>
                <td>{record.processingRate}/min</td>
                <td>{record.efficiency}%</td>
                <td>{record.performanceScore}/100</td>
                <td>
                  <Badge tone={record.statusTone}>{record.status}</Badge>
                </td>
                <td>
                  <button
                    className="performance-analytics__button"
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onSelect(record);
                    }}
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
