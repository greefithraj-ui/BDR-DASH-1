import { MetricCard } from "../../../components/design-system";
import type { PerformanceKpi } from "../performanceAnalytics.types";

type PerformanceKpiRowProps = {
  kpis: PerformanceKpi[];
};

export function PerformanceKpiRow({ kpis }: PerformanceKpiRowProps) {
  return (
    <div className="performance-analytics__kpi-row">
      {kpis.map((kpi) => (
        <MetricCard key={kpi.id} label={kpi.label} value={kpi.value} helper={kpi.delta} tone={kpi.deltaTone} />
      ))}
    </div>
  );
}
