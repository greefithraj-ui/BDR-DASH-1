import { Badge, Card } from "../../../components/design-system";
import type { FailureDistributionItem } from "../productAnalytics.types";

type FailureDistributionPanelProps = {
  items: FailureDistributionItem[];
};

export function FailureDistributionPanel({ items }: FailureDistributionPanelProps) {
  const total = items.reduce((sum, item) => sum + item.count, 0);

  return (
    <Card>
      <div className="product-analytics__section-header">
        <div>
          <p className="product-analytics__kicker">Failures</p>
          <h2>Failure Distribution</h2>
        </div>
        <Badge tone="warning">{total} events</Badge>
      </div>
      <div className="product-analytics__distribution">
        {items.map((item) => (
          <div key={item.cause} className="product-analytics__distribution-row">
            <span className="product-analytics__distribution-label">
              {item.cause}
              <small>{Math.round((item.count / total) * 100)}%</small>
            </span>
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
