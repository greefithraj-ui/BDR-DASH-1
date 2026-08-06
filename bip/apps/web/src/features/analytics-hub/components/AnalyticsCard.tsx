import { Badge, Card, ChartContainer } from "../../../components/design-system";
import type { AnalyticsCard as AnalyticsCardData } from "../analyticsHub.types";

type AnalyticsCardProps = {
  card: AnalyticsCardData;
  onPrimaryAction: (card: AnalyticsCardData) => void;
  onSecondaryAction: (card: AnalyticsCardData) => void;
};

export function AnalyticsCard({ card, onPrimaryAction, onSecondaryAction }: AnalyticsCardProps) {
  return (
    <Card className="analytics-hub__card" data-category={card.category}>
      <header className="analytics-hub__card-header">
        <div>
          <h3>{card.title}</h3>
          <p>{card.description}</p>
        </div>
        <Badge tone={card.statusTone}>{card.status}</Badge>
      </header>

      <div className="analytics-hub__card-metrics">
        {card.metrics.map((metric) => (
          <div key={metric.label} className="analytics-hub__card-metric">
            <strong className={metric.tone ? `analytics-hub__card-metric--${metric.tone}` : undefined}>{metric.value}</strong>
            <span>{metric.label}</span>
          </div>
        ))}
      </div>

      <ChartContainer className="analytics-hub__card-chart" height="72px" />

      <footer className="analytics-hub__card-actions">
        <button className="analytics-hub__button" type="button" onClick={() => onPrimaryAction(card)}>
          {card.primaryAction.label}
        </button>
        <button className="analytics-hub__button analytics-hub__button--soft" type="button" onClick={() => onSecondaryAction(card)}>
          {card.secondaryAction.label}
        </button>
      </footer>
    </Card>
  );
}
