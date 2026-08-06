import { Badge, EmptyState } from "../../components/design-system";
import { usePerformanceAnalytics } from "./usePerformanceAnalytics";
import { DistributionPanel } from "./components/DistributionPanel";
import { PerformanceComparison } from "./components/PerformanceComparison";
import { PerformanceDetailPanel } from "./components/PerformanceDetailPanel";
import { PerformanceKpiRow } from "./components/PerformanceKpiRow";
import { PerformanceTable } from "./components/PerformanceTable";
import { PerformanceToolbar } from "./components/PerformanceToolbar";
import { PerformanceTrendPlaceholder } from "./components/PerformanceTrendPlaceholder";
import "./performanceAnalytics.css";

export function PerformanceAnalyticsPage() {
  const performance = usePerformanceAnalytics();

  if (performance.selected) {
    return (
      <PerformanceDetailPanel
        record={performance.selected}
        chart={performance.charts[0]}
        onBack={performance.closeDetail}
      />
    );
  }

  return (
    <section className="performance-analytics" aria-labelledby="performance-analytics-title">
      <header className="performance-analytics__hero">
        <div>
          <p className="performance-analytics__eyebrow">Performance</p>
          <h1 id="performance-analytics-title">Performance Analytics</h1>
          <p className="performance-analytics__subtitle">
            Throughput, cycle time, machine utilization, processing rate, efficiency, and machine/product performance comparisons using mock data.
          </p>
        </div>
        <Badge tone="info">Mock Data</Badge>
      </header>

      <PerformanceToolbar
        filters={performance.filters}
        options={performance.options}
        onFiltersChange={performance.updateFilters}
        onClearAll={performance.clearFilters}
      />

      <div className="performance-analytics__summary-row">
        <p>
          {performance.records.length} records shown
          {performance.activeFilterCount > 0 ? ` · ${performance.activeFilterCount} active filter${performance.activeFilterCount === 1 ? "" : "s"}` : ""}
        </p>
      </div>

      <PerformanceKpiRow kpis={performance.kpis} />

      <div className="performance-analytics__summary-grid">
        <DistributionPanel kicker="Distribution" title="Cycle Distribution" badgeLabel="Cycle time" items={performance.cycleDistribution} />
        <DistributionPanel kicker="Distribution" title="Utilization Distribution" badgeLabel="Utilization" items={performance.utilizationDistribution} />
      </div>

      <PerformanceTrendPlaceholder trend={performance.trend} charts={performance.charts} />

      <div className="performance-analytics__comparison-grid">
        <PerformanceComparison kicker="Comparison" title="Machine Comparison" items={performance.machineComparisons} />
        <PerformanceComparison kicker="Comparison" title="Product Performance" items={performance.productComparisons} />
      </div>

      {performance.records.length === 0 ? (
        <EmptyState label="No performance records match the current filters" />
      ) : (
        <PerformanceTable records={performance.records} onSelect={performance.openDetail} />
      )}
    </section>
  );
}
