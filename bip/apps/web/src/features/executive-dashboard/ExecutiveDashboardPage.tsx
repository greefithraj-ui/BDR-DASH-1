import {
  Badge,
  Card,
  ChartContainer,
  LoadingSkeleton,
  MetricCard
} from "../../components/design-system";
import { ApiErrorState } from "../../components/feedback/ApiErrorState";
import { describeApiError } from "../../lib/errors";
import { useExecutiveDashboard } from "./useExecutiveDashboard";
import "./executiveDashboard.css";

export function ExecutiveDashboardPage() {
  const { data, error, isLoading, refresh } = useExecutiveDashboard();

  if (isLoading) {
    return <LoadingSkeleton className="executive-dashboard__loading" label="Loading executive dashboard" />;
  }

  if (error) {
    return <ApiErrorState message={describeApiError(error)} onRetry={() => void refresh()} />;
  }

  return (
    <section className="executive-dashboard" aria-labelledby="executive-dashboard-title">
      <header className="executive-dashboard__hero">
        <div>
          <p className="executive-dashboard__eyebrow">Executive Dashboard</p>
          <h1 id="executive-dashboard-title">Battery Intelligence Platform</h1>
          <p className="executive-dashboard__subtitle">
            Executive operating view backed by live collector and database data.
          </p>
        </div>
        <button className="ds-button" type="button" onClick={() => void refresh()}>
          Refresh
        </button>
        <Badge tone="info">Live Data</Badge>
      </header>

      <section className="executive-dashboard__kpi-grid" aria-label="Executive KPIs">
        {data.kpis.map((kpi) => (
          <MetricCard
            key={kpi.id}
            helper={kpi.helper}
            label={kpi.label}
            tone={kpi.tone}
            value={kpi.value}
          />
        ))}
      </section>

      <section className="executive-dashboard__main-grid">
        <Card className="executive-dashboard__summary">
          <div className="executive-dashboard__section-header">
            <div>
              <p className="executive-dashboard__section-kicker">Summary</p>
              <h2>Executive Summary</h2>
            </div>
            <Badge>Placeholder</Badge>
          </div>
          <p>
            Coming Soon
          </p>
        </Card>

        <Card>
          <div className="executive-dashboard__section-header">
            <div>
              <p className="executive-dashboard__section-kicker">Operations</p>
              <h2>Operations Overview</h2>
            </div>
          </div>
          <div className="executive-dashboard__operations-grid">
            {data.operations.map((item) => (
              <article key={item.id} className="executive-dashboard__operation-card">
                <Badge tone={item.tone}>{item.value}</Badge>
                <h3>{item.title}</h3>
                <p>{item.description}</p>
              </article>
            ))}
          </div>
        </Card>
      </section>

      <section className="executive-dashboard__panel-grid">
        <Card>
          <div className="executive-dashboard__section-header">
            <div>
              <p className="executive-dashboard__section-kicker">Activity</p>
              <h2>Recent Activity</h2>
            </div>
          </div>
          <div className="executive-dashboard__stack">
            {data.activity.map((item) => (
              <article key={item.id} className="executive-dashboard__activity-row">
                <time>{item.timestamp}</time>
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.context}</p>
                </div>
              </article>
            ))}
          </div>
        </Card>

        <Card>
          <div className="executive-dashboard__section-header">
            <div>
              <p className="executive-dashboard__section-kicker">Alerts</p>
              <h2>Alerts</h2>
            </div>
          </div>
          <div className="executive-dashboard__stack">
            {data.alerts.map((alert) => (
              <article key={alert.id} className="executive-dashboard__alert-row">
                <Badge tone={alert.severity}>{alert.severity}</Badge>
                <div>
                  <h3>{alert.title}</h3>
                  <p>{alert.description}</p>
                </div>
              </article>
            ))}
          </div>
        </Card>
      </section>

      <Card>
        <div className="executive-dashboard__section-header">
          <div>
            <p className="executive-dashboard__section-kicker">Performance</p>
            <h2>Performance Overview</h2>
          </div>
          <Badge>Chart Placeholders</Badge>
        </div>
        <div className="executive-dashboard__chart-grid">
          {data.performance.map((chart) => (
            <ChartContainer key={chart.id}>
              <div>
                <h3>{chart.title}</h3>
                <p>{chart.description}</p>
              </div>
            </ChartContainer>
          ))}
        </div>
      </Card>
    </section>
  );
}
