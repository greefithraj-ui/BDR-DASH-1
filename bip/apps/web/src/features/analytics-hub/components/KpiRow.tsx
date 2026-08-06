import { MetricCard } from "../../../components/design-system";
import type { AnalyticsKpi } from "../analyticsHub.types";

type KpiRowProps = {
  kpis: AnalyticsKpi[];
};

export function KpiRow({ kpis }: KpiRowProps) {
  return (
    <div className="analytics-hub__kpi-row">
      {kpis.map((kpi) => (
        <MetricCard key={kpi.id} label={kpi.label} value={kpi.value} helper={kpi.delta} tone={kpi.deltaTone} />
      ))}
    </div>
  );
}
