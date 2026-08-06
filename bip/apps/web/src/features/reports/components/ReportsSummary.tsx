import { MetricCard } from "../../../components/design-system";
import type { ReportsKpi } from "../reports.types";

type ReportsSummaryProps = {
  kpis: ReportsKpi[];
  shownCount: number;
  activeFilterCount: number;
};

export function ReportsSummary({ kpis, shownCount, activeFilterCount }: ReportsSummaryProps) {
  return (
    <div className="reports__summary">
      <div className="reports__kpi-row">
        {kpis.map((kpi) => (
          <MetricCard key={kpi.id} label={kpi.label} value={kpi.value} helper={kpi.delta} tone={kpi.deltaTone} />
        ))}
      </div>
      <div className="reports__summary-row">
        <p>
          {shownCount} reports shown
          {activeFilterCount > 0 ? ` · ${activeFilterCount} active filter${activeFilterCount === 1 ? "" : "s"}` : ""}
        </p>
      </div>
    </div>
  );
}
