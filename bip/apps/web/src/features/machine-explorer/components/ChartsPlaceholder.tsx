import { ChartContainer } from "../../../components/design-system";
import type { MachineDetail } from "../machineExplorer.types";

type ChartsPlaceholderProps = {
  detail: MachineDetail;
};

export function ChartsPlaceholder({ detail }: ChartsPlaceholderProps) {
  const { charts } = detail;

  return (
    <section className="machine-explorer-detail__chart-grid" aria-label="Placeholder charts">
      {charts.map((chart) => (
        <ChartContainer key={chart.id} title={chart.title} description={chart.description} />
      ))}
    </section>
  );
}
