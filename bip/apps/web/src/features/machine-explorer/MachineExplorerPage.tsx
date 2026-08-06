import { Badge, EmptyState, LoadingSkeleton } from "../../components/design-system";
import { ApiErrorState } from "../../components/feedback/ApiErrorState";
import { describeApiError } from "../../lib/errors";
import { useMachineDetail } from "./useMachineDetail";
import { useMachineExplorer } from "./useMachineExplorer";
import { MachineCard } from "./components/MachineCard";
import { MachineDetail } from "./components/MachineDetail";
import { MachineSearchToolbar } from "./components/MachineSearchToolbar";
import "./machineExplorer.css";

export function MachineExplorerPage() {
  const explorer = useMachineExplorer();
  const detail = useMachineDetail(explorer.selected);

  if (explorer.selected && detail.detail) {
    return (
      <MachineDetail
        detail={detail.detail}
        isLoading={detail.isLoading}
        errorMessage={detail.error ? describeApiError(detail.error) : null}
        onRefresh={() => void detail.refresh()}
        onRetry={() => void detail.refresh()}
        onBack={explorer.closeDetail}
      />
    );
  }

  if (explorer.isLoading) {
    return <LoadingSkeleton className="machine-explorer__loading" label="Loading machine explorer" />;
  }

  if (explorer.error) {
    return <ApiErrorState message={describeApiError(explorer.error)} onRetry={() => void explorer.refresh()} />;
  }

  return (
    <section className="machine-explorer" aria-labelledby="machine-explorer-title">
      <header className="machine-explorer__hero">
        <div>
          <p className="machine-explorer__eyebrow">Machine Explorer</p>
          <h1 id="machine-explorer-title">Machine Explorer</h1>
          <p className="machine-explorer__subtitle">
            Search, filter, sort, and inspect machines and their battery slots using live collector and database data.
          </p>
        </div>
        <button className="machine-explorer__button" type="button" onClick={() => void explorer.refresh()}>
          Refresh
        </button>
        <Badge tone="info">Live Data</Badge>
      </header>

      <MachineSearchToolbar
        filters={explorer.filters}
        options={explorer.options}
        sort={explorer.sort}
        onFiltersChange={explorer.updateFilters}
        onClearAll={explorer.clearFilters}
        onSort={explorer.toggleSort}
      />

      <div className="machine-explorer__summary-row">
        <p>
          {explorer.filteredCount} machines found
          {explorer.activeFilterCount > 0 ? ` · ${explorer.activeFilterCount} active filter${explorer.activeFilterCount === 1 ? "" : "s"}` : ""}
        </p>
        <p className="machine-explorer__summary-sort">
          Sorted by {explorer.sort.column} ({explorer.sort.direction})
        </p>
      </div>

      {explorer.filteredMachines.length === 0 ? (
        <EmptyState label="No machines match the current filters" />
      ) : (
        <div className="machine-explorer__grid">
          {explorer.filteredMachines.map((machine) => (
            <MachineCard key={machine.id} machine={machine} onSelect={explorer.openDetail} />
          ))}
        </div>
      )}
    </section>
  );
}