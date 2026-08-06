import { Badge, EmptyState, LoadingSkeleton } from "../../components/design-system";
import { ApiErrorState } from "../../components/feedback/ApiErrorState";
import { describeApiError } from "../../lib/errors";
import { useQualityAnalytics } from "./useQualityAnalytics";
import { DefectDistributionPanel } from "./components/DefectDistributionPanel";
import { FailureCategoriesPanel } from "./components/FailureCategoriesPanel";
import { QualityComparison } from "./components/QualityComparison";
import { QualityDetailPanel } from "./components/QualityDetailPanel";
import { QualityKpiRow } from "./components/QualityKpiRow";
import { QualityTable } from "./components/QualityTable";
import { QualityToolbar } from "./components/QualityToolbar";
import { QualityTrendPlaceholder } from "./components/QualityTrendPlaceholder";
import "./qualityAnalytics.css";

export function QualityAnalyticsPage() {
  const quality = useQualityAnalytics();

  if (quality.selected) {
    return (
      <QualityDetailPanel
        record={quality.selected}
        chart={quality.charts[0]}
        onBack={quality.closeDetail}
      />
    );
  }

  if (quality.isLoading) {
    return <LoadingSkeleton className="quality-analytics__loading" label="Loading quality analytics" />;
  }

  if (quality.error) {
    return <ApiErrorState message={describeApiError(quality.error)} onRetry={() => void quality.refresh()} />;
  }

  return (
    <section className="quality-analytics" aria-labelledby="quality-analytics-title">
      <header className="quality-analytics__hero">
        <div>
          <p className="quality-analytics__eyebrow">Quality</p>
          <h1 id="quality-analytics-title">Quality Analytics</h1>
          <p className="quality-analytics__subtitle">
            Pass/fail rates, yield, retest rate, defect distribution, failure categories, and product/machine quality comparisons from live fleet data.
          </p>
        </div>
        <button className="quality-analytics__button" type="button" onClick={() => void quality.refresh()}>
          Refresh
        </button>
        <Badge tone="info">Live Data</Badge>
      </header>

      <QualityToolbar
        filters={quality.filters}
        options={quality.options}
        onFiltersChange={quality.updateFilters}
        onClearAll={quality.clearFilters}
      />

      <div className="quality-analytics__summary-row">
        <p>
          {quality.records.length} records shown
          {quality.activeFilterCount > 0 ? ` · ${quality.activeFilterCount} active filter${quality.activeFilterCount === 1 ? "" : "s"}` : ""}
        </p>
      </div>

      <QualityKpiRow kpis={quality.kpis} />

      <div className="quality-analytics__summary-grid">
        <DefectDistributionPanel items={quality.defectDistribution} />
        <FailureCategoriesPanel items={quality.failureCategories} />
      </div>

      <QualityTrendPlaceholder trend={quality.trend} charts={quality.charts} />

      <div className="quality-analytics__comparison-grid">
        <QualityComparison kicker="Comparison" title="Product Quality Comparison" items={quality.productComparisons} />
        <QualityComparison kicker="Comparison" title="Machine Quality Comparison" items={quality.machineComparisons} />
      </div>

      {quality.records.length === 0 ? (
        <EmptyState label="No quality records match the current filters" />
      ) : (
        <QualityTable records={quality.records} onSelect={quality.openDetail} />
      )}
    </section>
  );
}
