import { Badge, Card } from "../../../components/design-system";
import type { SystemHealthItem } from "../batteryIntelligence.types";
import { SectionHeader } from "./SectionHeader";

type SystemHealthPanelProps = {
  items: SystemHealthItem[];
};

export function SystemHealthPanel({ items }: SystemHealthPanelProps) {
  return (
    <Card>
      <SectionHeader eyebrow="System" title="System Health Panel" />
      <div className="battery-intelligence__system-grid">
        {items.map((item) => (
          <div key={item.id} className="battery-intelligence__system-item">
            <span>{item.label}</span>
            <Badge tone={item.tone}>{item.value}</Badge>
          </div>
        ))}
      </div>
    </Card>
  );
}
