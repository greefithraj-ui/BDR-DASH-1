import { Badge, Card } from "../../../components/design-system";
import type { ProductFirmwareSummary } from "../productAnalytics.types";

type FirmwareSummaryPanelProps = {
  items: ProductFirmwareSummary[];
};

export function FirmwareSummaryPanel({ items }: FirmwareSummaryPanelProps) {
  const total = items.reduce((sum, item) => sum + item.count, 0);

  return (
    <Card>
      <div className="product-analytics__section-header">
        <div>
          <p className="product-analytics__kicker">Firmware</p>
          <h2>Firmware Summary</h2>
        </div>
        <Badge tone="info">{total} batteries</Badge>
      </div>
      <div className="product-analytics__distribution">
        {items.map((item) => (
          <div key={item.firmware} className="product-analytics__distribution-row">
            <span className="product-analytics__distribution-label">{item.firmware}</span>
            <div className="product-analytics__distribution-track" aria-hidden="true">
              <div
                className="product-analytics__distribution-fill"
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
