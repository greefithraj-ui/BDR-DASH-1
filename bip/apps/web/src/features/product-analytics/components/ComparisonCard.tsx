import { Badge, Card } from "../../../components/design-system";
import type { ProductComparisonCard as ProductComparisonCardData } from "../productAnalytics.types";

type ComparisonCardProps = {
  card: ProductComparisonCardData;
};

export function ComparisonCard({ card }: ComparisonCardProps) {
  return (
    <Card className="product-analytics__comparison-card" data-tone={card.statusTone}>
      <header className="product-analytics__comparison-header">
        <div>
          <h3>{card.product}</h3>
          <p>{card.comparison}</p>
        </div>
        <Badge tone={card.statusTone}>{card.statusTone}</Badge>
      </header>
      <div className="product-analytics__comparison-metrics">
        {card.metrics.map((metric) => (
          <div key={metric.label} className="product-analytics__comparison-metric">
            <strong className={metric.tone ? `product-analytics__comparison-metric--${metric.tone}` : undefined}>{metric.value}</strong>
            <span>{metric.label}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
