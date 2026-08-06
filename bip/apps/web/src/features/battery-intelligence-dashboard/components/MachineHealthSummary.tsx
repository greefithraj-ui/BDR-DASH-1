import { Badge, Card } from "../../../components/design-system";
import type { MachineHealthItem } from "../batteryIntelligence.types";
import { SectionHeader } from "./SectionHeader";

type MachineHealthSummaryProps = {
  items: MachineHealthItem[];
};

export function MachineHealthSummary({ items }: MachineHealthSummaryProps) {
  return (
    <Card>
      <SectionHeader eyebrow="Machines" title="Machine Health Summary" />
      <div className="battery-intelligence__stack">
        {items.map((item) => (
          <article key={item.id} className="battery-intelligence__row">
            <div>
              <h3>{item.machine}</h3>
              <p>{item.detail}</p>
            </div>
            <Badge tone={item.tone}>{item.status}</Badge>
          </article>
        ))}
      </div>
    </Card>
  );
}
