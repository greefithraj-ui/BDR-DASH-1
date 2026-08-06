import { Badge } from "../../../components/design-system";
import { formatDuration } from "../reports.mock";
import type { Report } from "../reports.types";

type ReportCardProps = {
  report: Report;
  onSelect: (report: Report) => void;
};

export function ReportCard({ report, onSelect }: ReportCardProps) {
  return (
    <article className="reports__card" onClick={() => onSelect(report)}>
      <header className="reports__card-header">
        <div className="reports__card-badges">
          <Badge tone="info">{report.category}</Badge>
          <Badge tone={report.statusTone}>{report.status}</Badge>
        </div>
        <span className="reports__card-frequency">{report.frequency}</span>
      </header>
      <h3>{report.title}</h3>
      <p className="reports__card-description">{report.description}</p>
      <dl className="reports__card-meta">
        <div>
          <dt>Owner</dt>
          <dd>{report.owner}</dd>
        </div>
        <div>
          <dt>Next Run</dt>
          <dd>{report.nextScheduledRun}</dd>
        </div>
        <div>
          <dt>Duration</dt>
          <dd>{formatDuration(report.estimatedDurationSeconds)}</dd>
        </div>
        <div>
          <dt>Pages</dt>
          <dd>{report.pages}</dd>
        </div>
      </dl>
      <button className="reports__button reports__card-button" type="button" onClick={() => onSelect(report)}>
        View report
      </button>
    </article>
  );
}
