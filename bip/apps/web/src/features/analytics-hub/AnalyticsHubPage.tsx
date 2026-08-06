import { useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Badge, LoadingSkeleton } from "../../components/design-system";
import { ApiErrorState } from "../../components/feedback/ApiErrorState";
import { describeApiError } from "../../lib/errors";
import { useAnalyticsHub } from "./useAnalyticsHub";
import { AlertsPanel } from "./components/AlertsPanel";
import { AnalyticsCardGrid } from "./components/AnalyticsCardGrid";
import { ChartsArea } from "./components/ChartsArea";
import { InsightsPanel } from "./components/InsightsPanel";
import { KpiRow } from "./components/KpiRow";
import { QuickNavSection } from "./components/QuickNavSection";
import type { AnalyticsCard } from "./analyticsHub.types";
import "./analyticsHub.css";

export function AnalyticsHubPage() {
  const hub = useAnalyticsHub();
  const navigate = useNavigate();
  const chartsRef = useRef<HTMLDivElement>(null);

  const openCategory = (card: AnalyticsCard) => {
    navigate(card.route);
  };

  const viewCharts = () => {
    chartsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  if (hub.isLoading) {
    return <LoadingSkeleton className="analytics-hub__loading" label="Loading analytics hub" />;
  }

  if (hub.error) {
    return <ApiErrorState message={describeApiError(hub.error)} onRetry={() => void hub.refresh()} />;
  }

  return (
    <section className="analytics-hub" aria-labelledby="analytics-hub-title">
      <header className="analytics-hub__hero">
        <div>
          <p className="analytics-hub__eyebrow">Analytics</p>
          <h1 id="analytics-hub-title">Analytics Hub</h1>
          <p className="analytics-hub__subtitle">
            Executive KPIs and category summaries across machines, products, quality, reliability, performance, trends, and comparisons.
          </p>
        </div>
        <button className="analytics-hub__button" type="button" onClick={() => void hub.refresh()}>
          Refresh
        </button>
        <Badge tone="info">Live Data</Badge>
      </header>

      <section className="analytics-hub__section" aria-label="Executive KPI summary">
        <div className="analytics-hub__section-header">
          <div>
            <p className="analytics-hub__kicker">Executive</p>
            <h2>KPI Summary</h2>
          </div>
        </div>
        <KpiRow kpis={hub.kpis} />
      </section>

      <section className="analytics-hub__section" aria-label="Analytics categories">
        <div className="analytics-hub__section-header">
          <div>
            <p className="analytics-hub__kicker">Categories</p>
            <h2>Analytics Navigation</h2>
          </div>
        </div>
        <AnalyticsCardGrid cards={hub.cards} onPrimaryAction={openCategory} onSecondaryAction={viewCharts} />
      </section>

      <div ref={chartsRef} className="analytics-hub__panel-grid">
        <InsightsPanel insights={hub.insights} />
        <AlertsPanel alerts={hub.alerts} />
      </div>

      <QuickNavSection items={hub.quickNav} onNavigate={navigate} />
      <ChartsArea charts={hub.charts} />
    </section>
  );
}