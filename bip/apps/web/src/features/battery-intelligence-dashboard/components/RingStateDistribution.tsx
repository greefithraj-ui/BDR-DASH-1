import { Badge, Card, ChartContainer } from "../../../components/design-system";
import type { RingStateItem } from "../batteryIntelligence.types";
import { SectionHeader } from "./SectionHeader";

type RingStateDistributionProps = {
  items: RingStateItem[];
};

export function RingStateDistribution({ items }: RingStateDistributionProps) {
  return (
    <Card>
      <SectionHeader eyebrow="Rings" title="Ring State Distribution" badge="Placeholder Chart" />
      <ChartContainer className="battery-intelligence__compact-chart">
        <div className="battery-intelligence__ring-list">
          {items.map((item) => (
            <div key={item.id} className="battery-intelligence__ring-state">
              <span>{item.state}</span>
              <Badge tone={item.tone}>{item.value}</Badge>
            </div>
          ))}
        </div>
      </ChartContainer>
    </Card>
  );
}
