import { Badge, Card, MetricCard } from "../../../components/design-system";
import type {
  FleetLifecycleItem,
  ProductChartPlaceholder,
  ProductComparisonCard,
  ProductRecord,
  ProductTone
} from "../productAnalytics.types";
import { ChartsPlaceholder } from "./ChartsPlaceholder";
import { FirmwareSummaryPanel } from "./FirmwareSummaryPanel";

function toneForStage(stage: string): ProductTone {
  switch (stage) {
    case "Review":
      return "warning";
    case "Pending Removal":
      return "danger";
    case "Finalized":
      return "success";
    case "Tracking":
      return "info";
    default:
      return "neutral";
  }
}

type ProductDetailPanelProps = {
  product: ProductRecord;
  comparison: ProductComparisonCard | null;
  charts: ProductChartPlaceholder[];
  onBack: () => void;
};

export function ProductDetailPanel({ product, comparison, charts, onBack }: ProductDetailPanelProps) {
  const lifecycle: FleetLifecycleItem[] = product.lifecycleDistribution.map((item) => ({
    stage: item.stage,
    count: item.count,
    tone: toneForStage(item.stage)
  }));

  return (
    <section className="product-analytics-detail" aria-labelledby="product-detail-title">
      <header className="product-analytics-detail__hero">
        <div>
          <button className="product-analytics__button" type="button" onClick={onBack}>
            ← Back to products
          </button>
          <p className="product-analytics__kicker">Product Detail</p>
          <h1 id="product-detail-title">{product.product}</h1>
          <p className="product-analytics-detail__subtitle">
            {product.category} · {product.description}
          </p>
        </div>
        <Badge tone={product.statusTone}>{product.status}</Badge>
      </header>

      <Card>
        <div className="product-analytics__section-header">
          <div>
            <p className="product-analytics__kicker">Overview</p>
            <h2>Current Metrics</h2>
          </div>
          <Badge tone="info">Live Data</Badge>
        </div>
        <div className="product-analytics-detail__metric-grid">
          <MetricCard label="Total Batteries" value={String(product.totalBatteries)} />
          <MetricCard label="Active" value={String(product.activeBatteries)} />
          <MetricCard label="Pending Removal" value={String(product.pendingRemoval)} tone={product.pendingRemoval > 0 ? "warning" : "neutral"} />
          <MetricCard label="Finalized" value={String(product.finalized)} />
          <MetricCard label="Failed" value={String(product.failed)} tone={product.failed > 0 ? "danger" : "neutral"} />
          <MetricCard label="Pass Rate" value={`${product.passRate}%`} tone={product.passRate >= 95 ? "success" : "info"} />
          <MetricCard label="Health Score" value={`${product.healthScore}/100`} tone={product.healthScore >= 80 ? "success" : "info"} />
          <MetricCard label="Avg Cycle" value={product.avgCycle} />
        </div>
      </Card>

      <div className="product-analytics-detail__grid">
        <FirmwareSummaryPanel items={product.firmwareSummary} />
        <Card>
          <div className="product-analytics__section-header">
            <div>
              <p className="product-analytics__kicker">Lifecycle</p>
              <h2>Lifecycle Distribution</h2>
            </div>
            <Badge tone="info">{product.totalBatteries} batteries</Badge>
          </div>
          <div className="product-analytics__distribution">
            {lifecycle.map((item) => (
              <div key={item.stage} className="product-analytics__distribution-row">
                <span className="product-analytics__distribution-label">{item.stage}</span>
                <div className="product-analytics__distribution-track" aria-hidden="true">
                  <div
                    className="product-analytics__distribution-fill product-analytics__distribution-fill--tone"
                    data-tone={item.tone}
                    style={{ width: `${Math.round((item.count / product.totalBatteries) * 100)}%` }}
                  />
                </div>
                <strong>{item.count}</strong>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <div className="product-analytics__section-header">
          <div>
            <p className="product-analytics__kicker">Deployment</p>
            <h2>Machines</h2>
          </div>
          <Badge tone="info">{product.machines.length} machines</Badge>
        </div>
        <div className="product-analytics-detail__machines">
          {product.machines.map((machine) => (
            <span key={machine} className="product-analytics-detail__machine-chip">
              {machine}
            </span>
          ))}
        </div>
      </Card>

      {comparison ? (
        <Card>
          <div className="product-analytics__section-header">
            <div>
              <p className="product-analytics__kicker">Comparison</p>
              <h2>Fleet Comparison</h2>
            </div>
            <Badge tone="info">{comparison.comparison}</Badge>
          </div>
          <div className="product-analytics-detail__metric-grid">
            {comparison.metrics.map((metric) => (
              <MetricCard key={metric.label} label={metric.label} value={metric.value} tone={metric.tone} />
            ))}
          </div>
        </Card>
      ) : null}

      <ChartsPlaceholder charts={charts} />
    </section>
  );
}
