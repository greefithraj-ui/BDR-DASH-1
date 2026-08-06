import { Badge, Card } from "../../../components/design-system";
import { formatDuration } from "../reports.mock";
import type { Report } from "../reports.types";

type ReportTableProps = {
  reports: Report[];
  onSelect: (report: Report) => void;
};

export function ReportTable({ reports, onSelect }: ReportTableProps) {
  return (
    <Card>
      <div className="reports__section-header">
        <div>
          <p className="reports__kicker">Library</p>
          <h2>Report Library</h2>
        </div>
        <Badge tone="info">{reports.length} reports</Badge>
      </div>
      <div className="reports__table-scroll">
        <table className="reports__table">
          <thead>
            <tr>
              <th scope="col">Title</th>
              <th scope="col">Category</th>
              <th scope="col">Owner</th>
              <th scope="col">Frequency</th>
              <th scope="col">Status</th>
              <th scope="col">Last Run</th>
              <th scope="col">Next Run</th>
              <th scope="col">Pages</th>
              <th scope="col">Duration</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {reports.map((report) => (
              <tr key={report.id} className="reports__row" onClick={() => onSelect(report)}>
                <td className="reports__strong">{report.title}</td>
                <td>{report.category}</td>
                <td>{report.owner}</td>
                <td>{report.frequency}</td>
                <td>
                  <Badge tone={report.statusTone}>{report.status}</Badge>
                </td>
                <td>{report.lastRun}</td>
                <td>{report.nextScheduledRun}</td>
                <td>{report.pages}</td>
                <td>{formatDuration(report.estimatedDurationSeconds)}</td>
                <td>
                  <button
                    className="reports__button"
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onSelect(report);
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
