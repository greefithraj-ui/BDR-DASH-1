import { Badge, Card, ChartContainer, MetricCard } from "../../../components/design-system";
import { formatDuration } from "../reports.mock";
import type { Report, ReportHistoryEntry } from "../reports.types";
import { ReportHistoryPanel } from "./ReportHistoryPanel";
import { ReportPreviewPanel } from "./ReportPreviewPanel";
import { ReportSchedulePanel } from "./ReportSchedulePanel";

type ReportDetailPanelProps = {
  report: Report;
  entries: ReportHistoryEntry[];
  onBack: () => void;
};

export function ReportDetailPanel({ report, entries, onBack }: ReportDetailPanelProps) {
  return (
    <section className="reports-detail" aria-labelledby="report-detail-title">
      <header className="reports-detail__hero">
        <div>
          <button className="reports__button" type="button" onClick={onBack}>
            ← Back to reports
          </button>
          <p className="reports__kicker">Report Detail</p>
          <h1 id="report-detail-title">{report.title}</h1>
          <p className="reports-detail__subtitle">{report.description}</p>
        </div>
        <div className="reports-detail__badges">
          <Badge tone="info">{report.category}</Badge>
          <Badge tone={report.statusTone}>{report.status}</Badge>
          <Badge tone="neutral">{report.frequency}</Badge>
        </div>
      </header>

      <Card>
        <div className="reports__section-header">
          <div>
            <p className="reports__kicker">Metadata</p>
            <h2>Report Metadata</h2>
          </div>
          <Badge tone="info">Live Data</Badge>
        </div>
        <div className="reports-detail__metric-grid">
          <MetricCard label="Owner" value={report.owner} />
          <MetricCard label="Created" value={report.createdDate} />
          <MetricCard label="Last Run" value={report.lastRun} />
          <MetricCard label="Next Run" value={report.nextScheduledRun} />
          <MetricCard label="Pages" value={String(report.pages)} />
          <MetricCard label="Duration" value={formatDuration(report.estimatedDurationSeconds)} />
        </div>
      </Card>

      <div className="reports-detail__grid">
        <ReportSchedulePanel report={report} />
        <ReportHistoryPanel kicker="Execution" title="Execution History" entries={entries} />
      </div>

      <ReportPreviewPanel report={report} />

      <section className="reports-detail__charts" aria-label="Report placeholder charts">
        <div className="reports__section-header">
          <div>
            <p className="reports__kicker">Charts</p>
            <h2>Placeholder Charts</h2>
          </div>
          <Badge tone="info">ChartContainer only</Badge>
        </div>
        <div className="reports-detail__chart-grid">
          <ChartContainer title="Report Content Trend" description="Placeholder chart container for report content over time." />
          <ChartContainer title="Report Volume by Category" description="Placeholder chart container for report volume by category." />
        </div>
      </section>
    </section>
  );
}
