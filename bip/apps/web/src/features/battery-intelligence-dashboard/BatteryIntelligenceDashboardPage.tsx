import { Badge, LoadingSkeleton } from "../../components/design-system";
import { ApiErrorState } from "../../components/feedback/ApiErrorState";
import { describeApiError } from "../../lib/errors";
import { ActiveMachineOverview } from "./components/ActiveMachineOverview";
import { BatteryLifecycleOverview } from "./components/BatteryLifecycleOverview";
import { BatteryStatusOverview } from "./components/BatteryStatusOverview";
import { CollectorStatusPanel } from "./components/CollectorStatusPanel";
import { MachineHealthSummary } from "./components/MachineHealthSummary";
import { PendingRemovalMonitor } from "./components/PendingRemovalMonitor";
import { PlaceholderCharts } from "./components/PlaceholderCharts";
import { RecentBatteryEvents } from "./components/RecentBatteryEvents";
import { RingStateDistribution } from "./components/RingStateDistribution";
import { SystemHealthPanel } from "./components/SystemHealthPanel";
import { useBatteryIntelligenceDashboard } from "./useBatteryIntelligenceDashboard";
import "./batteryIntelligence.css";

export function BatteryIntelligenceDashboardPage() {
  const { data, error, isLoading, refresh } = useBatteryIntelligenceDashboard();

  if (isLoading) {
    return <LoadingSkeleton className="battery-intelligence__loading" label="Loading battery intelligence" />;
  }

  if (error) {
    return <ApiErrorState message={describeApiError(error)} onRetry={() => void refresh()} />;
  }

  return (
    <section className="battery-intelligence" aria-labelledby="battery-intelligence-title">
      <header className="battery-intelligence__hero">
        <div>
          <p className="battery-intelligence__eyebrow">Battery Intelligence Dashboard</p>
          <h1 id="battery-intelligence-title">Engineering and Operator View</h1>
          <p className="battery-intelligence__subtitle">
            Operational workspace for battery tracking, machine context, collector status, and system health backed by live data.
          </p>
        </div>
        <button className="ds-button" type="button" onClick={() => void refresh()}>
          Refresh
        </button>
        <Badge tone="info">Live Data</Badge>
      </header>

      <BatteryStatusOverview metrics={data.statusMetrics} />

      <section className="battery-intelligence__two-column">
        <MachineHealthSummary items={data.machineHealth} />
        <RingStateDistribution items={data.ringStates} />
      </section>

      <section className="battery-intelligence__wide-stack">
        <ActiveMachineOverview items={data.activeMachines} />
        <BatteryLifecycleOverview items={data.lifecycle} />
      </section>

      <section className="battery-intelligence__three-column">
        <CollectorStatusPanel items={data.collectorStatus} />
        <PendingRemovalMonitor items={data.pendingRemovals} />
        <SystemHealthPanel items={data.systemHealth} />
      </section>

      <RecentBatteryEvents items={data.recentEvents} />
      <PlaceholderCharts charts={data.charts} />
    </section>
  );
}
