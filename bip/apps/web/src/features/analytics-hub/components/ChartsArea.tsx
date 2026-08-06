import { ChartContainer } from "../../../components/design-system";
import type { AnalyticsChartPlaceholder } from "../analyticsHub.types";

type ChartsAreaProps = {
  charts: AnalyticsChartPlaceholder[];
};

export function ChartsArea({ charts }: ChartsAreaProps) {
  return (
    <section className="analytics-hub__charts-area" id="analytics-charts" aria-label="Placeholder charts">
      <div className="analytics-hub__section-header">
        <div>
          <p className="analytics-hub__kicker">Charts</p>
          <h2>Placeholder Chart Area</h2>
        </div>
      </div>
      <div className="analytics-hub__chart-grid">
        {charts.map((chart) => (
          <ChartContainer key={chart.id} title={chart.title} description={chart.description} />
        ))}
      </div>
    </section>
  );
}
