import { Badge, Card } from "../../../components/design-system";
import type { ProductRecord } from "../productAnalytics.types";

type ProductHealthSummaryProps = {
  products: ProductRecord[];
};

export function ProductHealthSummary({ products }: ProductHealthSummaryProps) {
  return (
    <Card>
      <div className="product-analytics__section-header">
        <div>
          <p className="product-analytics__kicker">Health</p>
          <h2>Product Health Summary</h2>
        </div>
        <Badge tone="info">{products.length} products</Badge>
      </div>
      <div className="product-analytics__health-list">
        {products.map((product) => (
          <div key={product.id} className="product-analytics__health-row">
            <div className="product-analytics__health-label">
              <strong>{product.product}</strong>
              <Badge tone={product.statusTone}>{product.status}</Badge>
            </div>
            <div className="product-analytics__health-track" aria-hidden="true">
              <div className="product-analytics__health-fill" style={{ width: `${product.healthScore}%` }} />
            </div>
            <span className="product-analytics__health-value">{product.healthScore}/100</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
