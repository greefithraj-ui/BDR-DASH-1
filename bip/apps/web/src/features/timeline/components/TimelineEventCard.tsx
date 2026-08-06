import { Badge } from "../../../components/design-system";
import type { TimelineEvent } from "../timeline.types";

type TimelineEventCardProps = {
  event: TimelineEvent;
  onSelect: (event: TimelineEvent) => void;
};

export function TimelineEventCard({ event, onSelect }: TimelineEventCardProps) {
  return (
    <article
      className="timeline__event-card"
      role="button"
      tabIndex={0}
      onClick={() => onSelect(event)}
      onKeyDown={(keyboardEvent) => {
        if (keyboardEvent.key === "Enter" || keyboardEvent.key === " ") {
          keyboardEvent.preventDefault();
          onSelect(event);
        }
      }}
    >
      <div className="timeline__event-time">
        <time>{event.timestamp.slice(11)}</time>
      </div>

      <div className="timeline__event-body">
        <header className="timeline__event-header">
          <Badge tone={event.tone}>{event.type}</Badge>
          <span className="timeline__event-meta">
            {event.batterySerialNumber} · {event.machineId} · {event.slot}
          </span>
        </header>
        <p className="timeline__event-reason">{event.reason}</p>
        <footer className="timeline__event-footer">
          {event.previousState ? (
            <span className="timeline__state-transition">
              <span className="timeline__state timeline__state--previous">{event.previousState}</span>
              <span aria-hidden="true">→</span>
              <span className="timeline__state timeline__state--current">{event.currentState}</span>
            </span>
          ) : (
            <span className="timeline__state timeline__state--current">{event.currentState}</span>
          )}
          <span className="timeline__event-full-time">{event.timestamp}</span>
        </footer>
      </div>
    </article>
  );
}
