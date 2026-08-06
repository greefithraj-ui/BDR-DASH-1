import { Badge, Card } from "../../../components/design-system";
import type { PerformanceComparisonItem } from "../performanceAnalytics.types";

type PerformanceComparisonProps = {
  kicker: string;
  title: string;
  items: PerformanceComparisonItem[];
};

export function PerformanceComparison({ kicker, title, items }: PerformanceComparisonProps) {
  return (
    <section className="performance-analytics__comparison" aria-label={title}>
      <div className="performance-analytics__section-header">
        <div>
          <p className="performance-analytics__kicker">{kicker}</p>
          <h2>{title}</h2>
        </div>
        <Badge tone="info">{items.length} vs fleet</Badge>
      </div>
      <div className="performance-analytics__comparison-grid">
        {items.map((item) => (
          <Card key={item.id} className="performance-analytics__comparison-card" data-tone={item.statusTone}>
            <header className="performance-analytics__comparison-header">
              <div>
                <h3>{item.name}</h3>
                <p>vs fleet average</p>
              </div>
              <Badge tone={item.kind === "Machine" ? "info" : "neutral"}>{item.kind}</Badge>
            </header>
            <div className="performance-analytics__comparison-metrics">
              {item.metrics.map((metric) => (
                <div key={metric.label} className="performance-analytics__comparison-metric">
                  <strong className={metric.tone ? `performance-analytics__comparison-metric--${metric.tone}` : undefined}>{metric.value}</strong>
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
