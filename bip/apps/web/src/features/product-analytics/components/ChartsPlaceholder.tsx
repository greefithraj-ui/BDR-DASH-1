import { ChartContainer } from "../../../components/design-system";
import type { ProductChartPlaceholder } from "../productAnalytics.types";

type ChartsPlaceholderProps = {
  charts: ProductChartPlaceholder[];
};

export function ChartsPlaceholder({ charts }: ChartsPlaceholderProps) {
  return (
    <section className="product-analytics__chart-grid" aria-label="Placeholder charts">
      {charts.map((chart) => (
        <ChartContainer key={chart.id} title={chart.title} description={chart.description} />
      ))}
    </section>
  );
}
