import { Badge, Card } from "../../../components/design-system";
import type { QualityFailureCategoryItem } from "../qualityAnalytics.types";

type FailureCategoriesPanelProps = {
  items: QualityFailureCategoryItem[];
};

export function FailureCategoriesPanel({ items }: FailureCategoriesPanelProps) {
  return (
    <Card>
      <div className="quality-analytics__section-header">
        <div>
          <p className="quality-analytics__kicker">Quality</p>
          <h2>Failure Categories</h2>
        </div>
        <Badge tone="info">{items.length} categories</Badge>
      </div>
      <ul className="quality-analytics__category-list">
        {items.map((item) => (
          <li key={item.id} className="quality-analytics__category-row">
            <div className="quality-analytics__category-head">
              <div>
                <strong>{item.category}</strong>
                <p>{item.description}</p>
              </div>
              <Badge tone={item.tone}>{item.severity}</Badge>
            </div>
            <div className="quality-analytics__category-meta">
              <span>{item.count} defects</span>
              <span>{item.share}% share</span>
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}
