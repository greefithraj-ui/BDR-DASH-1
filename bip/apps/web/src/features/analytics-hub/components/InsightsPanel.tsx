import { Badge, Card } from "../../../components/design-system";
import type { Insight } from "../analyticsHub.types";

type InsightsPanelProps = {
  insights: Insight[];
};

export function InsightsPanel({ insights }: InsightsPanelProps) {
  return (
    <Card>
      <div className="analytics-hub__section-header">
        <div>
          <p className="analytics-hub__kicker">Intelligence</p>
          <h2>Recent Insights</h2>
        </div>
        <Badge tone="info">Live Data</Badge>
      </div>
      <div className="analytics-hub__insight-list">
        {insights.map((insight) => (
          <article key={insight.id} className="analytics-hub__insight">
            <div className="analytics-hub__insight-meta">
              <Badge tone={insight.tagTone}>{insight.tag}</Badge>
              <time>{insight.timestamp}</time>
            </div>
            <h3>{insight.title}</h3>
            <p>{insight.detail}</p>
          </article>
        ))}
      </div>
    </Card>
  );
}
