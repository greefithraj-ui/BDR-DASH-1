import { Badge, Card, ChartContainer, MetricCard } from "../../../components/design-system";
import type { QualityChartPlaceholder, QualityRecord } from "../qualityAnalytics.types";

type QualityDetailPanelProps = {
  record: QualityRecord;
  chart: QualityChartPlaceholder;
  onBack: () => void;
};

export function QualityDetailPanel({ record, chart, onBack }: QualityDetailPanelProps) {
  return (
    <section className="quality-analytics-detail" aria-labelledby="quality-detail-title">
      <header className="quality-analytics-detail__hero">
        <div>
          <button className="quality-analytics__button" type="button" onClick={onBack}>
            ← Back to quality records
          </button>
          <p className="quality-analytics__kicker">Quality Detail</p>
          <h1 id="quality-detail-title">
            {record.product} · {record.machine}
          </h1>
          <p className="quality-analytics-detail__subtitle">
            {record.category} · firmware {record.firmware} · {record.date}
          </p>
        </div>
        <Badge tone={record.statusTone}>{record.result}</Badge>
      </header>

      <Card>
        <div className="quality-analytics__section-header">
          <div>
            <p className="quality-analytics__kicker">Overview</p>
            <h2>Quality Metrics</h2>
          </div>
          <Badge tone="info">Live Data</Badge>
        </div>
        <div className="quality-analytics-detail__metric-grid">
          <MetricCard label="Produced" value={String(record.produced)} />
          <MetricCard label="Passed" value={String(record.passed)} />
          <MetricCard label="Failed" value={String(record.failed)} tone={record.failed > 0 ? "danger" : "neutral"} />
          <MetricCard label="Retested" value={String(record.retested)} />
          <MetricCard label="Pass Rate" value={`${record.passRate}%`} tone={record.passRate >= 95 ? "success" : "danger"} />
          <MetricCard label="Fail Rate" value={`${record.failRate}%`} tone={record.failRate > 5 ? "warning" : "neutral"} />
          <MetricCard label="Yield" value={`${record.yield}%`} tone={record.yield >= 96 ? "success" : "warning"} />
          <MetricCard label="Retest Rate" value={`${record.retestRate}%`} tone={record.retestRate > 4 ? "warning" : "neutral"} />
          <MetricCard label="Quality Score" value={`${record.qualityScore}/100`} tone={record.qualityScore >= 80 ? "success" : "warning"} />
        </div>
      </Card>

      <Card>
        <div className="quality-analytics__section-header">
          <div>
            <p className="quality-analytics__kicker">Defects</p>
            <h2>Defect Distribution</h2>
          </div>
          <Badge tone={record.statusTone}>{record.status}</Badge>
        </div>
        <div className="quality-analytics__distribution">
          {record.defects.map((defect) => (
            <div key={defect.id} className="quality-analytics__distribution-row">
              <span className="quality-analytics__distribution-label">{defect.category}</span>
              <div className="quality-analytics__distribution-track" aria-hidden="true">
                <div
                  className="quality-analytics__distribution-fill quality-analytics__distribution-fill--tone"
                  data-tone={defect.tone}
                  style={{ width: `${Math.round((defect.count / record.failed) * 100)}%` }}
                />
              </div>
              <strong>{defect.count}</strong>
            </div>
          ))}
        </div>
      </Card>

      <ChartContainer title={chart.title} description={chart.description} />
    </section>
  );
}
