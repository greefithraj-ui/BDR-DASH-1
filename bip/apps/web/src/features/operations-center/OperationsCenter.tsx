import { LoadingSkeleton } from "../../components/design-system";
import { ApiErrorState } from "../../components/feedback/ApiErrorState";
import { describeApiError } from "../../lib/errors";

import { CommandBar } from "./components/CommandBar";
import { LivePipeline } from "./components/LivePipeline";
import { OperationalQueue } from "./components/OperationalQueue";
import { InspectorWorkspace } from "./components/InspectorWorkspace";

import { useOperationsCenter } from "./useOperationsCenter";
import "./operationsCenter.css";

export function OperationsCenter() {
  const {
    searchQuery,
    setSearchQuery,
    selectedRingId,
    setSelectedRingId,
    lastRefreshTime,
    data,
    error,
    isLoading,
    refresh
  } = useOperationsCenter();

  if (isLoading) {
    return (
      <LoadingSkeleton
        className="opsc-loading"
        label="Loading Operations Command Center telemetry..."
      />
    );
  }

  if (error) {
    return (
      <ApiErrorState
        message={describeApiError(error)}
        onRetry={() => void refresh()}
      />
    );
  }

  return (
    <section className="opsc-dashboard" aria-labelledby="opsc-dashboard-title">
      {/* Top Command Bar */}
      <CommandBar 
        onRefresh={() => void refresh()} 
        lastRefreshTime={lastRefreshTime} 
        isHealthy={data.isSystemHealthy} 
      />

      {/* Split Pane Layout */}
      <div className="opsc-split-layout">
        
        {/* Left Pane: Pipeline & Queue */}
        <div className="opsc-pane-left">
          <LivePipeline stages={data.pipelineStages} onSelectRing={setSelectedRingId} />
          <OperationalQueue 
            exceptions={data.sortedExceptions} 
            selectedRingId={selectedRingId} 
            onSelectRing={setSelectedRingId} 
          />
        </div>

        {/* Right Pane: Inspector */}
        <div className="opsc-pane-right">
          <InspectorWorkspace focus={data.currentFocus} />
        </div>

      </div>
    </section>
  );
}
