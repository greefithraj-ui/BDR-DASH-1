import { Badge } from "../../../components/design-system";
import type { MachineDetail as MachineDetailData } from "../machineExplorer.types";
import { BatteryList } from "./BatteryList";
import { ChartsPlaceholder } from "./ChartsPlaceholder";
import { HealthPanel } from "./HealthPanel";
import { MachineInfoCard } from "./MachineInfoCard";
import { MachineStats } from "./MachineStats";
import { RecentEvents } from "./RecentEvents";
import { SlotOverview } from "./SlotOverview";
import { TimelinePlaceholder } from "./TimelinePlaceholder";

type MachineDetailProps = {
  detail: MachineDetailData;
  isLoading: boolean;
  errorMessage: string | null;
  onRefresh: () => void;
  onRetry: () => void;
  onBack: () => void;
};

export function MachineDetail({ detail, isLoading, errorMessage, onRefresh, onRetry, onBack }: MachineDetailProps) {
  const { record } = detail;

  return (
    <section className="machine-explorer-detail" aria-labelledby="machine-detail-title">
      <header className="machine-explorer-detail__hero">
        <div>
          <button className="machine-explorer__button" type="button" onClick={onBack}>
            ← Back to machines
          </button>
          <p className="machine-explorer-detail__kicker">Machine Detail</p>
          <h1 id="machine-detail-title">{record.machineId}</h1>
          <p className="machine-explorer-detail__subtitle">
            Live information, statistics, and state panels for {record.name}.
          </p>
        </div>
        <button className="machine-explorer__button" type="button" onClick={onRefresh}>
          Refresh
        </button>
        <Badge tone="info">Live Data</Badge>
      </header>

      {errorMessage ? (
        <div className="machine-explorer-detail__status">
          <Badge tone="danger">Cached</Badge>
          <span>{errorMessage}. Showing the last known state.</span>
          <button className="machine-explorer__button" type="button" onClick={onRetry}>
            Retry
          </button>
        </div>
      ) : isLoading ? (
        <div className="machine-explorer-detail__status">
          <Badge tone="info">Refreshing</Badge>
          <span>Refreshing the latest machine state…</span>
        </div>
      ) : null}

      <div className="machine-explorer-detail__grid">
        <MachineInfoCard detail={detail} />
        <MachineStats detail={detail} />
      </div>

      <SlotOverview detail={detail} />

      <div className="machine-explorer-detail__grid">
        <HealthPanel detail={detail} />
        <TimelinePlaceholder detail={detail} />
      </div>

      <BatteryList detail={detail} />
      <RecentEvents detail={detail} />
      <ChartsPlaceholder detail={detail} />
    </section>
  );
}