import { ChartContainer } from "../../../components/design-system";
import type { ChartPlaceholderItem } from "../batteryExplorer.types";

type DetailPlaceholderChartsProps = {
  charts: ChartPlaceholderItem[];
};

export function DetailPlaceholderCharts({ charts }: DetailPlaceholderChartsProps) {
  return (
    <section className="battery-explorer-detail__chart-grid" aria-label="Placeholder charts">
      {charts.map((chart) => (
        <ChartContainer key={chart.id} title={chart.title} description={chart.description} />
      ))}
    </section>
  );
}
