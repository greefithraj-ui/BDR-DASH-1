import { Badge, Card, ChartContainer } from "../../../components/design-system";
import type { PerformanceChartPlaceholder, PerformanceTrendPoint } from "../performanceAnalytics.types";

type PerformanceTrendPlaceholderProps = {
  trend: PerformanceTrendPoint[];
  charts: PerformanceChartPlaceholder[];
};

export function PerformanceTrendPlaceholder({ trend, charts }: PerformanceTrendPlaceholderProps) {
  const recent = trend.slice(-7);

  return (
    <section className="performance-analytics__trend" aria-label="Performance trend placeholders">
      <div className="performance-analytics__section-header">
        <div>
          <p className="performance-analytics__kicker">Trends</p>
          <h2>Performance Trends</h2>
        </div>
        <Badge tone="info">Last 7 days</Badge>
      </div>

      <div className="performance-analytics__chart-grid">
        {charts.map((chart) => (
          <ChartContainer key={chart.id} title={chart.title} description={chart.description} />
        ))}
      </div>

      <Card>
        <div className="performance-analytics__section-header">
          <div>
            <p className="performance-analytics__kicker">Trend Data</p>
            <h3 className="performance-analytics__trend-title">Recent Points</h3>
          </div>
        </div>
        <table className="performance-analytics__trend-table">
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Throughput</th>
              <th scope="col">Utilization</th>
              <th scope="col">Cycle Time</th>
              <th scope="col">Efficiency</th>
            </tr>
          </thead>
          <tbody>
            {recent.map((point) => (
              <tr key={point.date}>
                <td className="performance-analytics__strong">{point.date}</td>
                <td>{point.throughput}/hr</td>
                <td>{point.utilization}%</td>
                <td>{point.cycleTime}s</td>
                <td>{point.efficiency}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </section>
  );
}
