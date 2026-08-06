import { Badge, Card } from "../../../components/design-system";
import type { PendingRemovalItem } from "../batteryIntelligence.types";
import { SectionHeader } from "./SectionHeader";

type PendingRemovalMonitorProps = {
  items: PendingRemovalItem[];
};

export function PendingRemovalMonitor({ items }: PendingRemovalMonitorProps) {
  return (
    <Card>
      <SectionHeader eyebrow="Removal" title="Pending Removal Monitor" badge="Mock" />
      <div className="battery-intelligence__stack">
        {items.map((item) => (
          <article key={item.id} className="battery-intelligence__removal-row">
            <div>
              <h3>{item.batteryId}</h3>
              <p>
                {item.ring} · {item.reason}
              </p>
            </div>
            <Badge tone={item.tone}>{item.age}</Badge>
          </article>
        ))}
      </div>
    </Card>
  );
}
