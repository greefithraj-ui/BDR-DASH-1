import { Badge, Card } from "../../../components/design-system";
import type { QualityComparisonItem } from "../qualityAnalytics.types";

type QualityComparisonProps = {
  kicker: string;
  title: string;
  items: QualityComparisonItem[];
};

export function QualityComparison({ kicker, title, items }: QualityComparisonProps) {
  return (
    <section className="quality-analytics__comparison" aria-label={title}>
      <div className="quality-analytics__section-header">
        <div>
          <p className="quality-analytics__kicker">{kicker}</p>
          <h2>{title}</h2>
        </div>
        <Badge tone="info">{items.length} vs fleet</Badge>
      </div>
      <div className="quality-analytics__comparison-grid">
        {items.map((item) => (
          <Card key={item.id} className="quality-analytics__comparison-card" data-tone={item.statusTone}>
            <header className="quality-analytics__comparison-header">
              <div>
                <h3>{item.name}</h3>
                <p>vs fleet average</p>
              </div>
              <Badge tone={item.kind === "Product" ? "info" : "neutral"}>{item.kind}</Badge>
            </header>
            <div className="quality-analytics__comparison-metrics">
              {item.metrics.map((metric) => (
                <div key={metric.label} className="quality-analytics__comparison-metric">
                  <strong className={metric.tone ? `quality-analytics__comparison-metric--${metric.tone}` : undefined}>{metric.value}</strong>
                  <span>{metric.label}</span>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </section>
  );
}
