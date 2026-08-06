import { Link } from "react-router-dom";
import { Badge, Card } from "../../../components/design-system";
import type { OperationalEvent } from "../useOperationsDashboard";

type RecentEventsFeedProps = {
  events: OperationalEvent[];
};

export function RecentEventsFeed({ events }: RecentEventsFeedProps) {
  return (
    <Card className="ops-events-card">
      <div className="ops-panel-header">
        <h2>RECENT LIFECYCLE EVENTS (LIVE FEED)</h2>
        <Link to="/timeline" className="ops-action-link">
          View Global Event Feed ➔
        </Link>
      </div>

      <div className="ops-events-feed">
        {events.length === 0 ? (
          <p className="ops-empty-text">No recent events reported.</p>
        ) : (
          events.map((ev) => (
            <div key={ev.id} className="ops-event-row">
              <span className="ops-event-time">{ev.formattedTime}</span>
              <Badge tone="neutral" className="ops-event-type">
                {ev.type}
              </Badge>
              <span className="ops-event-target">
                Target:{" "}
                <Link
                  to={`/battery-explorer?ringId=${encodeURIComponent(ev.ringId)}`}
                  className="ops-ring-link"
                >
                  {ev.ringId}
                </Link>
              </span>
              <span className="ops-event-machine">Station: {ev.machineId}</span>
              <span className="ops-event-msg">{ev.message}</span>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
