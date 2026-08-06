import { Badge, Card } from "../../../components/design-system";
import type { FleetLifecycleItem } from "../productAnalytics.types";

type LifecycleDistributionPanelProps = {
  items: FleetLifecycleItem[];
};

export function LifecycleDistributionPanel({ items }: LifecycleDistributionPanelProps) {
  const total = items.reduce((sum, item) => sum + item.count, 0);

  return (
    <Card>
      <div className="product-analytics__section-header">
        <div>
          <p className="product-analytics__kicker">Lifecycle</p>
          <h2>Lifecycle Distribution</h2>
        </div>
        <Badge tone="info">{total} batteries</Badge>
      </div>
      <div className="product-analytics__distribution">
        {items.map((item) => (
          <div key={item.stage} className="product-analytics__distribution-row">
            <span className="product-analytics__distribution-label">{item.stage}</span>
            <div className="product-analytics__distribution-track" aria-hidden="true">
              <div
                className="product-analytics__distribution-fill product-analytics__distribution-fill--tone"
                data-tone={item.tone}
                style={{ width: `${Math.round((item.count / total) * 100)}%` }}
              />
            </div>
            <strong>{item.count}</strong>
          </div>
        ))}
      </div>
    </Card>
  );
}
