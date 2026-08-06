import { Badge, LoadingSkeleton } from "../../components/design-system";
import { ApiErrorState } from "../../components/feedback/ApiErrorState";
import { describeApiError } from "../../lib/errors";
import { useBatteryDetail } from "./useBatteryDetail";
import { useBatteryExplorer } from "./useBatteryExplorer";
import { ActiveFilterChips } from "./components/ActiveFilterChips";
import { BatteryDetail } from "./components/BatteryDetail";
import { BatteryExplorerTable } from "./components/BatteryExplorerTable";
import { ExplorerPagination } from "./components/ExplorerPagination";
import { ExplorerToolbar } from "./components/ExplorerToolbar";
import "./batteryExplorer.css";

export function BatteryExplorerPage() {
  const explorer = useBatteryExplorer();
  const detail = useBatteryDetail(explorer.selected);

  if (explorer.selected && detail.detail) {
    return (
      <BatteryDetail
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
    return <LoadingSkeleton className="battery-explorer__loading" label="Loading battery explorer" />;
  }

  if (explorer.error) {
    return <ApiErrorState message={describeApiError(explorer.error)} onRetry={() => void explorer.refresh()} />;
  }

  return (
    <section className="battery-explorer" aria-labelledby="battery-explorer-title">
      <header className="battery-explorer__hero">
        <div>
          <p className="battery-explorer__eyebrow">Battery Explorer</p>
          <h1 id="battery-explorer-title">Battery Explorer</h1>
          <p className="battery-explorer__subtitle">
            Search, filter, sort, and inspect batteries across rings and machines using live collector and database data.
          </p>
        </div>
        <button className="battery-explorer__button" type="button" onClick={() => void explorer.refresh()}>
          Refresh
        </button>
        <Badge tone="info">Live Data</Badge>
      </header>

      <ExplorerToolbar
        filters={explorer.filters}
        options={explorer.options}
        onChange={explorer.updateFilters}
        onClearAll={explorer.clearFilters}
      />

      <ActiveFilterChips
        filters={explorer.filters}
        onRemove={explorer.removeFilter}
        onClearAll={explorer.clearFilters}
      />

      <div className="battery-explorer__summary-row">
        <p>
          {explorer.filteredCount} batteries found
          {explorer.activeFilterCount > 0 ? ` · ${explorer.activeFilterCount} active filter${explorer.activeFilterCount === 1 ? "" : "s"}` : ""}
        </p>
        <p className="battery-explorer__summary-sort">Sorted by {explorer.sort.column}</p>
      </div>

      <BatteryExplorerTable
        records={explorer.pageRecords}
        sort={explorer.sort}
        onSort={explorer.toggleSort}
        onSelect={explorer.openDetail}
      />

      <ExplorerPagination
        page={explorer.page}
        pageCount={explorer.pageCount}
        total={explorer.filteredCount}
        onPageChange={explorer.changePage}
      />
    </section>
  );
}