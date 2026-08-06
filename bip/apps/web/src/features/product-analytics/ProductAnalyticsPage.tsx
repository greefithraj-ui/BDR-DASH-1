import { Badge, EmptyState, LoadingSkeleton } from "../../components/design-system";
import { ApiErrorState } from "../../components/feedback/ApiErrorState";
import { describeApiError } from "../../lib/errors";
import { useProductAnalytics } from "./useProductAnalytics";
import { ChartsPlaceholder } from "./components/ChartsPlaceholder";
import { ComparisonCard } from "./components/ComparisonCard";
import { FailureDistributionPanel } from "./components/FailureDistributionPanel";
import { FirmwareSummaryPanel } from "./components/FirmwareSummaryPanel";
import { LifecycleDistributionPanel } from "./components/LifecycleDistributionPanel";
import { ProductDetailPanel } from "./components/ProductDetailPanel";
import { ProductDistributionPanel } from "./components/ProductDistributionPanel";
import { ProductHealthSummary } from "./components/ProductHealthSummary";
import { ProductKpiRow } from "./components/ProductKpiRow";
import { ProductTable } from "./components/ProductTable";
import { ProductToolbar } from "./components/ProductToolbar";
import "./productAnalytics.css";

export function ProductAnalyticsPage() {
  const analytics = useProductAnalytics();

  if (analytics.selected) {
    const comparison = analytics.comparisonCards.find((card) => card.product === analytics.selected?.product) ?? null;

    return (
      <ProductDetailPanel
        product={analytics.selected}
        comparison={comparison}
        charts={analytics.charts}
        onBack={analytics.closeDetail}
      />
    );
  }

  if (analytics.isLoading) {
    return <LoadingSkeleton className="product-analytics__loading" label="Loading product analytics" />;
  }

  if (analytics.error) {
    return <ApiErrorState message={describeApiError(analytics.error)} onRetry={() => void analytics.refresh()} />;
  }

  return (
    <section className="product-analytics" aria-labelledby="product-analytics-title">
      <header className="product-analytics__hero">
        <div>
          <p className="product-analytics__eyebrow">Production</p>
          <h1 id="product-analytics-title">Product Analytics</h1>
          <p className="product-analytics__subtitle">
            Product KPIs, firmware and lifecycle distribution, comparisons, and catalog insights from live fleet data.
          </p>
        </div>
        <button className="product-analytics__button" type="button" onClick={() => void analytics.refresh()}>
          Refresh
        </button>
        <Badge tone="info">Live Data</Badge>
      </header>

      <ProductToolbar
        filters={analytics.filters}
        options={analytics.options}
        onFiltersChange={analytics.updateFilters}
        onClearAll={analytics.clearFilters}
      />

      <div className="product-analytics__summary-row">
        <p>
          {analytics.products.length} products shown
          {analytics.activeFilterCount > 0 ? ` · ${analytics.activeFilterCount} active filter${analytics.activeFilterCount === 1 ? "" : "s"}` : ""}
        </p>
      </div>

      <ProductKpiRow kpis={analytics.kpis} />

      <div className="product-analytics__summary-grid">
        <FirmwareSummaryPanel items={analytics.fleetFirmware} />
        <ProductDistributionPanel items={analytics.distribution} />
        <FailureDistributionPanel items={analytics.failureDistribution} />
        <LifecycleDistributionPanel items={analytics.fleetLifecycle} />
      </div>

      <div className="product-analytics__grid">
        <ProductHealthSummary products={analytics.products} />
        <section className="product-analytics__comparison" aria-label="Product comparison cards">
          <div className="product-analytics__section-header">
            <div>
              <p className="product-analytics__kicker">Comparison</p>
              <h2>Product Comparison Cards</h2>
            </div>
          </div>
          <div className="product-analytics__comparison-grid">
            {analytics.comparisonCards.map((card) => (
              <ComparisonCard key={card.id} card={card} />
            ))}
          </div>
        </section>
      </div>

      {analytics.products.length === 0 ? (
        <EmptyState label="No products match the current filters" />
      ) : (
        <ProductTable products={analytics.products} onSelect={analytics.openDetail} />
      )}

      <ChartsPlaceholder charts={analytics.charts} />
    </section>
  );
}
