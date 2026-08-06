import { Badge, Card } from "../../../components/design-system";
import type { QualityRecord } from "../qualityAnalytics.types";

type QualityTableProps = {
  records: QualityRecord[];
  onSelect: (record: QualityRecord) => void;
};

export function QualityTable({ records, onSelect }: QualityTableProps) {
  return (
    <Card>
      <div className="quality-analytics__section-header">
        <div>
          <p className="quality-analytics__kicker">Records</p>
          <h2>Quality Table</h2>
        </div>
        <Badge tone="info">{records.length} records</Badge>
      </div>
      <div className="quality-analytics__table-scroll">
        <table className="quality-analytics__table">
          <thead>
            <tr>
              <th scope="col">Product</th>
              <th scope="col">Machine</th>
              <th scope="col">Firmware</th>
              <th scope="col">Date</th>
              <th scope="col">Produced</th>
              <th scope="col">Passed</th>
              <th scope="col">Failed</th>
              <th scope="col">Retested</th>
              <th scope="col">Pass Rate</th>
              <th scope="col">Yield</th>
              <th scope="col">Retest Rate</th>
              <th scope="col">Result</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {records.map((record) => (
              <tr key={record.id} className="quality-analytics__row" onClick={() => onSelect(record)}>
                <td className="quality-analytics__strong">{record.product}</td>
                <td>{record.machine}</td>
                <td>{record.firmware}</td>
                <td>{record.date}</td>
                <td>{record.produced}</td>
                <td>{record.passed}</td>
                <td>{record.failed}</td>
                <td>{record.retested}</td>
                <td>{record.passRate}%</td>
                <td>{record.yield}%</td>
                <td>{record.retestRate}%</td>
                <td>
                  <Badge tone={record.statusTone}>{record.result}</Badge>
                </td>
                <td>
                  <button
                    className="quality-analytics__button"
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
