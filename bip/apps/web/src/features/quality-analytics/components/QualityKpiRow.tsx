import { MetricCard } from "../../../components/design-system";
import type { QualityKpi } from "../qualityAnalytics.types";

type QualityKpiRowProps = {
  kpis: QualityKpi[];
};

export function QualityKpiRow({ kpis }: QualityKpiRowProps) {
  return (
    <div className="quality-analytics__kpi-row">
      {kpis.map((kpi) => (
        <MetricCard key={kpi.id} label={kpi.label} value={kpi.value} helper={kpi.delta} tone={kpi.deltaTone} />
      ))}
    </div>
  );
}
