import { Badge, Card, ChartContainer } from "../../../components/design-system";
import type { QualityChartPlaceholder, QualityTrendPoint } from "../qualityAnalytics.types";

type QualityTrendPlaceholderProps = {
  trend: QualityTrendPoint[];
  charts: QualityChartPlaceholder[];
};

export function QualityTrendPlaceholder({ trend, charts }: QualityTrendPlaceholderProps) {
  const recent = trend.slice(-7);

  return (
    <section className="quality-analytics__trend" aria-label="Quality trend placeholders">
      <div className="quality-analytics__section-header">
        <div>
          <p className="quality-analytics__kicker">Trends</p>
          <h2>Quality Trends</h2>
        </div>
        <Badge tone="info">Last 7 days</Badge>
      </div>

      <div className="quality-analytics__chart-grid">
        {charts.map((chart) => (
          <ChartContainer key={chart.id} title={chart.title} description={chart.description} />
        ))}
      </div>

      <Card>
        <div className="quality-analytics__section-header">
          <div>
            <p className="quality-analytics__kicker">Trend Data</p>
            <h3 className="quality-analytics__trend-title">Recent Points</h3>
          </div>
        </div>
        <table className="quality-analytics__trend-table">
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Pass Rate</th>
              <th scope="col">Yield</th>
              <th scope="col">Failed</th>
            </tr>
          </thead>
          <tbody>
            {recent.map((point) => (
              <tr key={point.date}>
                <td className="quality-analytics__strong">{point.date}</td>
                <td>{point.passRate}%</td>
                <td>{point.yield}%</td>
                <td>{point.failed}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </section>
  );
}
