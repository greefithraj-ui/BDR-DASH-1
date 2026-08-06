import { Badge, Card } from "../../../components/design-system";
import { formatDuration } from "../reports.mock";
import type { ReportHistoryEntry, ReportRunStatus } from "../reports.types";

const RUN_TONES: Record<ReportRunStatus, "success" | "danger" | "info"> = {
  Success: "success",
  Failed: "danger",
  Running: "info"
};

type ReportHistoryPanelProps = {
  kicker: string;
  title: string;
  entries: ReportHistoryEntry[];
};

export function ReportHistoryPanel({ kicker, title, entries }: ReportHistoryPanelProps) {
  return (
    <Card>
      <div className="reports__section-header">
        <div>
          <p className="reports__kicker">{kicker}</p>
          <h2>{title}</h2>
        </div>
        <Badge tone="info">{entries.length} runs</Badge>
      </div>
      <div className="reports__table-scroll">
        <table className="reports__table">
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Report</th>
              <th scope="col">Status</th>
              <th scope="col">Duration</th>
              <th scope="col">Pages</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.id}>
                <td>{entry.date}</td>
                <td className="reports__strong">{entry.reportTitle}</td>
                <td>
                  <Badge tone={RUN_TONES[entry.status]}>{entry.status}</Badge>
                </td>
                <td>{formatDuration(entry.durationSeconds)}</td>
                <td>{entry.pages}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
