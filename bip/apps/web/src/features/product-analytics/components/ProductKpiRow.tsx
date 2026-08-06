import { MetricCard } from "../../../components/design-system";
import type { ProductKpi } from "../productAnalytics.types";

type ProductKpiRowProps = {
  kpis: ProductKpi[];
};

export function ProductKpiRow({ kpis }: ProductKpiRowProps) {
  return (
    <div className="product-analytics__kpi-row">
      {kpis.map((kpi) => (
        <MetricCard key={kpi.id} label={kpi.label} value={kpi.value} helper={kpi.delta} tone={kpi.deltaTone} />
      ))}
    </div>
  );
}
