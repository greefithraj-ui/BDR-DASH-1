import { ChartContainer } from "../../../components/design-system";

export function TimelineChartsPlaceholder() {
  return (
    <section className="timeline-detail__chart-grid" aria-label="Placeholder charts">
      <ChartContainer
        title="Event Volume"
        description="Placeholder chart container for future event volume by period."
      />
      <ChartContainer
        title="Event Type Split"
        description="Placeholder chart container for future event type distribution."
      />
    </section>
  );
}
