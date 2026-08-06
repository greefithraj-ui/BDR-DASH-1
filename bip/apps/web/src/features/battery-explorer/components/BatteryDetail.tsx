import { Badge, Card } from "../../../components/design-system";
import type { BatteryDetail as BatteryDetailData } from "../batteryExplorer.types";
import { DetailCurrentContext } from "./DetailCurrentContext";
import { DetailIdentityCard } from "./DetailIdentityCard";
import { DetailLifecycleTimeline } from "./DetailLifecycleTimeline";
import { DetailPlaceholderCharts } from "./DetailPlaceholderCharts";
import { DetailRecentEvents } from "./DetailRecentEvents";

type BatteryDetailProps = {
  detail: BatteryDetailData;
  isLoading: boolean;
  errorMessage: string | null;
  onRefresh: () => void;
  onRetry: () => void;
  onBack: () => void;
};

export function BatteryDetail({ detail, isLoading, errorMessage, onRefresh, onRetry, onBack }: BatteryDetailProps) {
  const { record } = detail;

  return (
    <section className="battery-explorer-detail" aria-labelledby="battery-detail-title">
      <header className="battery-explorer-detail__hero">
        <div>
          <button className="battery-explorer__button" type="button" onClick={onBack}>
            ← Back to results
          </button>
          <p className="battery-explorer-detail__kicker">Battery Detail</p>
          <h1 id="battery-detail-title">{record.serialNumber}</h1>
          <p className="battery-explorer-detail__subtitle">
            Live identity, context, and state panels for {record.ringName}.
          </p>
        </div>
        <button className="battery-explorer__button" type="button" onClick={onRefresh}>
          Refresh
        </button>
        <Badge tone="info">Live Data</Badge>
      </header>

      {errorMessage ? (
        <div className="battery-explorer-detail__status">
          <Badge tone="danger">Cached</Badge>
          <span>{errorMessage}. Showing the last known state.</span>
          <button className="battery-explorer__button" type="button" onClick={onRetry}>
            Retry
          </button>
        </div>
      ) : isLoading ? (
        <div className="battery-explorer-detail__status">
          <Badge tone="info">Refreshing</Badge>
          <span>Refreshing the latest ring state…</span>
        </div>
      ) : null}

      <div className="battery-explorer-detail__grid">
        <DetailIdentityCard detail={detail} />
        <DetailCurrentContext detail={detail} />
        <DetailLifecycleTimeline stages={detail.lifecycle} />
      </div>

      <Card>
        <div className="battery-explorer-detail__section-header">
          <div>
            <p className="battery-explorer-detail__kicker">Decision</p>
            <h2>Decision Summary</h2>
          </div>
          <span className="battery-explorer-detail__placeholder-label">Placeholder</span>
        </div>
        <div className="battery-explorer-detail__decision">
          <div>
            <h3>{detail.decisionSummary.recommendation}</h3>
            <p>{detail.decisionSummary.confidence}</p>
          </div>
          <p>{detail.decisionSummary.note}</p>
        </div>
      </Card>

      <DetailRecentEvents events={detail.recentEvents} />
      <DetailPlaceholderCharts charts={detail.charts} />
    </section>
  );
}