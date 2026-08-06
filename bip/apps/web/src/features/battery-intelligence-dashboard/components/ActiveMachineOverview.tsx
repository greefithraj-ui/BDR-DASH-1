import { Badge, Card } from "../../../components/design-system";
import type { ActiveMachineItem } from "../batteryIntelligence.types";
import { SectionHeader } from "./SectionHeader";

type ActiveMachineOverviewProps = {
  items: ActiveMachineItem[];
};

export function ActiveMachineOverview({ items }: ActiveMachineOverviewProps) {
  return (
    <Card>
      <SectionHeader eyebrow="Operations" title="Active Machine Overview" />
      <div className="battery-intelligence__machine-grid">
        {items.map((item) => (
          <article key={item.id} className="battery-intelligence__machine-card">
            <h3>{item.name}</h3>
            <p>{item.currentRing}</p>
            <Badge tone={item.tone}>{item.operatorState}</Badge>
          </article>
        ))}
      </div>
    </Card>
  );
}
