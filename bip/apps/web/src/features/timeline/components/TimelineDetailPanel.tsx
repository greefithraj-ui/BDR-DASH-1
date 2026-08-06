import { Badge, Card, MetricCard } from "../../../components/design-system";
import type { TimelineEvent } from "../timeline.types";
import { TimelineChartsPlaceholder } from "./TimelineChartsPlaceholder";

type TimelineDetailPanelProps = {
  event: TimelineEvent;
  onBack: () => void;
};

export function TimelineDetailPanel({ event, onBack }: TimelineDetailPanelProps) {
  return (
    <section className="timeline-detail" aria-labelledby="timeline-detail-title">
      <header className="timeline-detail__hero">
        <div>
          <button className="timeline__button" type="button" onClick={onBack}>
            ← Back to timeline
          </button>
          <p className="timeline-detail__kicker">Timeline Detail</p>
          <h1 id="timeline-detail-title">{event.type}</h1>
          <p className="timeline-detail__subtitle">{event.reason}</p>
        </div>
        <Badge tone={event.tone}>{event.type}</Badge>
      </header>

      <Card>
        <div className="timeline-detail__section-header">
          <div>
            <p className="timeline-detail__kicker">Event</p>
            <h2>Event Information</h2>
          </div>
          <Badge tone="info">Live Data</Badge>
        </div>
        <div className="timeline-detail__metric-grid">
          <MetricCard label="Event Type" value={event.type} tone={event.tone} />
          <MetricCard label="Battery" value={event.batterySerialNumber} />
          <MetricCard label="Machine" value={event.machineId} />
          <MetricCard label="Slot" value={event.slot} />
          <MetricCard label="Timestamp" value={event.timestamp} />
          <MetricCard label="Reason" value={event.reason} />
        </div>
      </Card>

      <Card>
        <div className="timeline-detail__section-header">
          <div>
            <p className="timeline-detail__kicker">State</p>
            <h2>State Change</h2>
          </div>
          <Badge>Placeholder</Badge>
        </div>
        <div className="timeline-detail__state-change">
          <div className="timeline-detail__state-box">
            <span>Previous State</span>
            <strong>{event.previousState ?? "—"}</strong>
          </div>
          <span className="timeline-detail__state-arrow" aria-hidden="true">
            →
          </span>
          <div className="timeline-detail__state-box timeline-detail__state-box--current">
            <span>Current State</span>
            <strong>{event.currentState ?? "—"}</strong>
          </div>
        </div>
      </Card>

      <Card>
        <div className="timeline-detail__section-header">
          <div>
            <p className="timeline-detail__kicker">Context</p>
            <h2>Metadata</h2>
          </div>
          <span className="timeline-detail__placeholder-label">Mock</span>
        </div>
        <dl className="timeline-detail__metadata">
          {event.metadata.map((item) => (
            <div key={item.label} className="timeline-detail__metadata-row">
              <dt>{item.label}</dt>
              <dd>{item.value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <TimelineChartsPlaceholder />
    </section>
  );
}
