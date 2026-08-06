import { Card } from "../../../components/design-system";
import type { BatteryDetailEvent } from "../batteryExplorer.types";

type DetailRecentEventsProps = {
  events: BatteryDetailEvent[];
};

export function DetailRecentEvents({ events }: DetailRecentEventsProps) {
  return (
    <Card>
      <div className="battery-explorer-detail__section-header">
        <div>
          <p className="battery-explorer-detail__kicker">Events</p>
          <h2>Recent Events</h2>
        </div>
        <span className="battery-explorer-detail__placeholder-label">Placeholder</span>
      </div>
      <div className="battery-explorer-detail__events">
        {events.map((event) => (
          <article key={event.id} className="battery-explorer-detail__event-row">
            <time>{event.timestamp}</time>
            <div>
              <h3>{event.event}</h3>
              <p>{event.context}</p>
            </div>
          </article>
        ))}
      </div>
    </Card>
  );
}
