import { MetricCard } from "../../../components/design-system";
import type { BatteryStatusMetric } from "../batteryIntelligence.types";

type BatteryStatusOverviewProps = {
  metrics: BatteryStatusMetric[];
};

export function BatteryStatusOverview({ metrics }: BatteryStatusOverviewProps) {
  return (
    <section className="battery-intelligence__status-grid" aria-label="Battery Status Overview">
      {metrics.map((metric) => (
        <MetricCard
          key={metric.id}
          helper={metric.helper}
          label={metric.label}
          tone={metric.tone}
          value={metric.value}
        />
      ))}
    </section>
  );
}
