import { Card } from "../../../components/design-system";
import type { LifecycleStage } from "../batteryIntelligence.types";
import { SectionHeader } from "./SectionHeader";

type BatteryLifecycleOverviewProps = {
  items: LifecycleStage[];
};

export function BatteryLifecycleOverview({ items }: BatteryLifecycleOverviewProps) {
  return (
    <Card>
      <SectionHeader eyebrow="Lifecycle" title="Battery Lifecycle Overview" />
      <div className="battery-intelligence__lifecycle">
        {items.map((item) => (
          <article key={item.id} className="battery-intelligence__lifecycle-stage">
            <div className="battery-intelligence__lifecycle-count">{item.count}</div>
            <h3>{item.stage}</h3>
            <p>{item.description}</p>
          </article>
        ))}
      </div>
    </Card>
  );
}
