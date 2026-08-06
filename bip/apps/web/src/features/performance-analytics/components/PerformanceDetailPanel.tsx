import { Badge, Card, ChartContainer, MetricCard } from "../../../components/design-system";
import type { PerformanceChartPlaceholder, PerformanceRecord } from "../performanceAnalytics.types";

type PerformanceDetailPanelProps = {
  record: PerformanceRecord;
  chart: PerformanceChartPlaceholder;
  onBack: () => void;
};

export function PerformanceDetailPanel({ record, chart, onBack }: PerformanceDetailPanelProps) {
  const targetRatio = Math.round((record.throughput / record.targetThroughput) * 100);

  return (
    <section className="performance-analytics-detail" aria-labelledby="performance-detail-title">
      <header className="performance-analytics-detail__hero">
        <div>
          <button className="performance-analytics__button" type="button" onClick={onBack}>
            ← Back to performance records
          </button>
          <p className="performance-analytics__kicker">Performance Detail</p>
          <h1 id="performance-detail-title">
            {record.machine} · {record.product}
          </h1>
          <p className="performance-analytics-detail__subtitle">
            {record.category} · firmware {record.firmware} · {record.date}
          </p>
        </div>
        <Badge tone={record.statusTone}>{record.status}</Badge>
      </header>

      <Card>
        <div className="performance-analytics__section-header">
          <div>
            <p className="performance-analytics__kicker">Overview</p>
            <h2>Performance Metrics</h2>
          </div>
          <Badge tone="info">Mock Data</Badge>
        </div>
        <div className="performance-analytics-detail__metric-grid">
          <MetricCard label="Throughput" value={`${record.throughput}/hr`} tone={record.throughput >= record.targetThroughput ? "success" : "warning"} />
          <MetricCard label="Cycle Time" value={`${record.cycleTime}s`} tone={record.cycleTime <= 13 ? "success" : "warning"} />
          <MetricCard label="Machine Utilization" value={`${record.utilization}%`} tone={record.utilization >= 85 ? "success" : "warning"} />
          <MetricCard label="Battery Processing Rate" value={`${record.processingRate}/min`} />
          <MetricCard label="Machine Efficiency" value={`${record.efficiency}%`} tone={record.efficiency >= 90 ? "success" : "info"} />
          <MetricCard label="Performance Score" value={`${record.performanceScore}/100`} tone={record.performanceScore >= 85 ? "success" : record.performanceScore >= 70 ? "warning" : "danger"} />
          <MetricCard label="Produced" value={String(record.produced)} />
          <MetricCard label="Target Throughput" value={`${record.targetThroughput}/hr`} />
        </div>
      </Card>

      <Card>
        <div className="performance-analytics__section-header">
          <div>
            <p className="performance-analytics__kicker">Target</p>
            <h2>Throughput vs Target</h2>
          </div>
          <Badge tone={targetRatio >= 100 ? "success" : "warning"}>{targetRatio}% of target</Badge>
        </div>
        <div className="performance-analytics-detail__target">
          <div className="performance-analytics__distribution-row">
            <span className="performance-analytics__distribution-label">Throughput</span>
            <div className="performance-analytics__distribution-track" aria-hidden="true">
              <div
                className="performance-analytics__distribution-fill performance-analytics__distribution-fill--tone"
                data-tone={targetRatio >= 100 ? "success" : "warning"}
                style={{ width: `${Math.min(100, targetRatio)}%` }}
              />
            </div>
            <strong>{record.throughput}/hr</strong>
          </div>
        </div>
      </Card>

      <ChartContainer title={chart.title} description={chart.description} />
    </section>
  );
}
