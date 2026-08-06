import { Card } from "../../../components/design-system";
import type { MachineDetail } from "../machineExplorer.types";

type RecentEventsProps = {
  detail: MachineDetail;
};

export function RecentEvents({ detail }: RecentEventsProps) {
  const { recentEvents } = detail;

  return (
    <Card>
      <div className="machine-explorer-detail__section-header">
        <div>
          <p className="machine-explorer-detail__kicker">Events</p>
          <h2>Recent Events</h2>
        </div>
        <span className="machine-explorer-detail__placeholder-label">Placeholder</span>
      </div>
      <div className="machine-explorer-detail__events">
        {recentEvents.map((event) => (
          <article key={event.id} className="machine-explorer-detail__event-row">
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
