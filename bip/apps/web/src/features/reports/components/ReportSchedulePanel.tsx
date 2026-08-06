import { Badge, Card } from "../../../components/design-system";
import { formatDuration } from "../reports.mock";
import type { Report } from "../reports.types";

type ReportSchedulePanelProps = {
  report: Report;
};

export function ReportSchedulePanel({ report }: ReportSchedulePanelProps) {
  return (
    <Card>
      <div className="reports__section-header">
        <div>
          <p className="reports__kicker">Schedule</p>
          <h2>Report Schedule</h2>
        </div>
        <Badge tone="info">{report.frequency}</Badge>
      </div>
      <dl className="reports__schedule-list">
        <div>
          <dt>Frequency</dt>
          <dd>{report.frequency}</dd>
        </div>
        <div>
          <dt>Run Time</dt>
          <dd>{report.schedule.time}</dd>
        </div>
        <div>
          <dt>Days</dt>
          <dd>{report.schedule.days}</dd>
        </div>
        <div>
          <dt>Next Scheduled Run</dt>
          <dd>{report.nextScheduledRun}</dd>
        </div>
        <div>
          <dt>Estimated Duration</dt>
          <dd>{formatDuration(report.estimatedDurationSeconds)}</dd>
        </div>
        <div>
          <dt>Recipients</dt>
          <dd>
            {report.schedule.recipients.map((recipient) => (
              <span key={recipient} className="reports__chip">
                {recipient}
              </span>
            ))}
          </dd>
        </div>
      </dl>
    </Card>
  );
}
