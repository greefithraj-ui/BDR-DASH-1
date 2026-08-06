import { Badge, Card } from "../../../components/design-system";
import type { PerformanceDistributionItem } from "../performanceAnalytics.types";

type DistributionPanelProps = {
  kicker: string;
  title: string;
  badgeLabel: string;
  items: PerformanceDistributionItem[];
};

export function DistributionPanel({ kicker, title, badgeLabel, items }: DistributionPanelProps) {
  const total = items.reduce((sum, item) => sum + item.count, 0);

  return (
    <Card>
      <div className="performance-analytics__section-header">
        <div>
          <p className="performance-analytics__kicker">{kicker}</p>
          <h2>{title}</h2>
        </div>
        <Badge tone="info">{badgeLabel}</Badge>
      </div>
      <div className="performance-analytics__distribution">
        {items.map((item) => (
          <div key={item.bucket} className="performance-analytics__distribution-row">
            <span className="performance-analytics__distribution-label">
              {item.bucket}
              <small>{total > 0 ? Math.round((item.count / total) * 100) : 0}%</small>
            </span>
            <div className="performance-analytics__distribution-track" aria-hidden="true">
              <div
                className="performance-analytics__distribution-fill performance-analytics__distribution-fill--tone"
                data-tone={item.tone}
                style={{ width: `${total > 0 ? (item.count / total) * 100 : 0}%` }}
              />
            </div>
            <strong>{item.count}</strong>
          </div>
        ))}
      </div>
    </Card>
  );
}
