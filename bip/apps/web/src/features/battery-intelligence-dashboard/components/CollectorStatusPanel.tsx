import { Badge, Card } from "../../../components/design-system";
import type { CollectorStatusItem } from "../batteryIntelligence.types";
import { SectionHeader } from "./SectionHeader";

type CollectorStatusPanelProps = {
  items: CollectorStatusItem[];
};

export function CollectorStatusPanel({ items }: CollectorStatusPanelProps) {
  return (
    <Card>
      <SectionHeader eyebrow="Collector" title="Collector Status" badge="Mock" />
      <div className="battery-intelligence__status-list">
        {items.map((item) => (
          <div key={item.id} className="battery-intelligence__status-line">
            <span>{item.label}</span>
            <Badge tone={item.tone}>{item.value}</Badge>
          </div>
        ))}
      </div>
    </Card>
  );
}
