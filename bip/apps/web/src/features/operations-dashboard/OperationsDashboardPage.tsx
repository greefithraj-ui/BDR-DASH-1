import { LoadingSkeleton } from "../../components/design-system";
import { ApiErrorState } from "../../components/feedback/ApiErrorState";
import { describeApiError } from "../../lib/errors";
import { LivePipeline } from "./components/LivePipeline";
import { MachineQueuePanel } from "./components/MachineQueuePanel";
import { OperationsHeader } from "./components/OperationsHeader";
import { RecentEventsFeed } from "./components/RecentEventsFeed";
import { UrgentExceptionsPanel } from "./components/UrgentExceptionsPanel";
import { useOperationsDashboard } from "./useOperationsDashboard";
import "./operations.css";

export function OperationsDashboardPage() {
  const { data, error, isLoading, refresh } = useOperationsDashboard();

  if (isLoading) {
    return <LoadingSkeleton className="ops-loading" label="Loading Operations Command Center data..." />;
  }

  if (error) {
    return <ApiErrorState message={describeApiError(error)} onRetry={() => void refresh()} />;
  }

  return (
    <section className="ops-dashboard" aria-labelledby="ops-dashboard-title">
      <OperationsHeader
        isSystemHealthy={data.isSystemHealthy}
        activeRingsCount={data.activeRingsCount}
        pendingRemovalCount={data.pendingRemovalCount}
        onRefresh={() => void refresh()}
      />

      <LivePipeline stages={data.pipelineStages} />

      <div className="ops-dashboard__two-column">
        <UrgentExceptionsPanel exceptions={data.urgentExceptions} />
        <MachineQueuePanel machines={data.machineQueues} />
      </div>

      <RecentEventsFeed events={data.recentEvents} />
    </section>
  );
}
