import { Badge, Card } from "../../../components/design-system";
import type { QualityDefectDistributionItem } from "../qualityAnalytics.types";

type DefectDistributionPanelProps = {
  items: QualityDefectDistributionItem[];
};

export function DefectDistributionPanel({ items }: DefectDistributionPanelProps) {
  return (
    <Card>
      <div className="quality-analytics__section-header">
        <div>
          <p className="quality-analytics__kicker">Quality</p>
          <h2>Defect Distribution</h2>
        </div>
        <Badge tone="info">{items.length} categories</Badge>
      </div>
      <div className="quality-analytics__distribution">
        {items.map((item) => (
          <div key={item.category} className="quality-analytics__distribution-row">
            <span className="quality-analytics__distribution-label">
              {item.category}
              <small>{item.share}%</small>
            </span>
            <div className="quality-analytics__distribution-track" aria-hidden="true">
              <div
                className="quality-analytics__distribution-fill quality-analytics__distribution-fill--tone"
                data-tone={item.tone}
                style={{ width: `${item.share}%` }}
              />
            </div>
            <strong>{item.count}</strong>
          </div>
        ))}
      </div>
    </Card>
  );
}
