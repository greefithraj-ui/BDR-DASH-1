import { Card } from "../../../components/design-system";
import type { BatteryEventItem } from "../batteryIntelligence.types";
import { SectionHeader } from "./SectionHeader";

type RecentBatteryEventsProps = {
  items: BatteryEventItem[];
};

export function RecentBatteryEvents({ items }: RecentBatteryEventsProps) {
  return (
    <Card>
      <SectionHeader eyebrow="Events" title="Recent Battery Events" badge="Mock" />
      <div className="battery-intelligence__stack">
        {items.map((item) => (
          <article key={item.id} className="battery-intelligence__event-row">
            <time>{item.timestamp}</time>
            <div>
              <h3>{item.event}</h3>
              <p>
                {item.batteryId} · {item.context}
              </p>
            </div>
          </article>
        ))}
      </div>
    </Card>
  );
}
