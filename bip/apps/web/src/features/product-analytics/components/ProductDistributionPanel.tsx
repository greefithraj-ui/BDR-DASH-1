import { Badge, Card } from "../../../components/design-system";
import type { ProductDistributionItem } from "../productAnalytics.types";

type ProductDistributionPanelProps = {
  items: ProductDistributionItem[];
};

export function ProductDistributionPanel({ items }: ProductDistributionPanelProps) {
  return (
    <Card>
      <div className="product-analytics__section-header">
        <div>
          <p className="product-analytics__kicker">Mix</p>
          <h2>Product Distribution</h2>
        </div>
        <Badge tone="info">5 products</Badge>
      </div>
      <div className="product-analytics__distribution">
        {items.map((item) => (
          <div key={item.product} className="product-analytics__distribution-row">
            <span className="product-analytics__distribution-label">
              {item.product} <small>{item.share}%</small>
            </span>
            <div className="product-analytics__distribution-track" aria-hidden="true">
              <div className="product-analytics__distribution-fill" style={{ width: `${item.share}%` }} />
            </div>
            <strong>{item.count}</strong>
          </div>
        ))}
      </div>
    </Card>
  );
}
