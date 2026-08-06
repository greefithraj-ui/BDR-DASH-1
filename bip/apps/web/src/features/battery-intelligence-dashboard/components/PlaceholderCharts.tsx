import { Card, ChartContainer } from "../../../components/design-system";
import type { ChartPlaceholderItem } from "../batteryIntelligence.types";
import { SectionHeader } from "./SectionHeader";

type PlaceholderChartsProps = {
  charts: ChartPlaceholderItem[];
};

export function PlaceholderCharts({ charts }: PlaceholderChartsProps) {
  return (
    <Card>
      <SectionHeader eyebrow="Visuals" title="Placeholder Chart Containers" />
      <div className="battery-intelligence__chart-grid">
        {charts.map((chart) => (
          <ChartContainer key={chart.id}>
            <div>
              <h3>{chart.title}</h3>
              <p>{chart.description}</p>
            </div>
          </ChartContainer>
        ))}
      </div>
    </Card>
  );
}
