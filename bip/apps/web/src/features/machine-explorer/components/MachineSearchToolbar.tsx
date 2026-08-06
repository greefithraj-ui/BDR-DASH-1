import type {
  MachineExplorerFilters,
  MachineExplorerOptions,
  MachineExplorerSort,
  MachineExplorerSortColumn
} from "../machineExplorer.types";

type MachineSearchToolbarProps = {
  filters: MachineExplorerFilters;
  options: MachineExplorerOptions;
  sort: MachineExplorerSort;
  onFiltersChange: (patch: Partial<MachineExplorerFilters>) => void;
  onClearAll: () => void;
  onSort: (column: MachineExplorerSortColumn) => void;
};

const SORT_COLUMNS: { value: MachineExplorerSortColumn; label: string }[] = [
  { value: "machineId", label: "Machine" },
  { value: "healthScore", label: "Health Score" },
  { value: "activeBatteries", label: "Active Batteries" },
  { value: "lastSeen", label: "Last Seen" }
];

export function MachineSearchToolbar({ filters, options, sort, onFiltersChange, onClearAll, onSort }: MachineSearchToolbarProps) {
  return (
    <section className="machine-explorer__toolbar" aria-label="Machine explorer filters">
      <div className="machine-explorer__toolbar-group">
        <h2 className="machine-explorer__group-title">Search</h2>
        <div className="machine-explorer__toolbar-fields">
          <label className="machine-explorer__field" htmlFor="machine-search-query">
            <span className="machine-explorer__field-label">Machine</span>
            <input
              id="machine-search-query"
              className="machine-explorer__control"
              type="text"
              value={filters.query}
              placeholder="e.g. AQC-03 or Station"
              onChange={(event) => onFiltersChange({ query: event.target.value })}
            />
          </label>
        </div>
      </div>

      <div className="machine-explorer__toolbar-group">
        <h2 className="machine-explorer__group-title">Filters</h2>
        <div className="machine-explorer__toolbar-fields">
          <label className="machine-explorer__field" htmlFor="machine-status-filter">
            <span className="machine-explorer__field-label">Status</span>
            <select
              id="machine-status-filter"
              className="machine-explorer__control"
              value={filters.status}
              onChange={(event) => onFiltersChange({ status: event.target.value })}
            >
              <option value="">All statuses</option>
              {options.statuses.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>

          <label className="machine-explorer__field" htmlFor="machine-sort-column">
            <span className="machine-explorer__field-label">Sort by</span>
            <select
              id="machine-sort-column"
              className="machine-explorer__control"
              value={sort.column}
              onChange={(event) => onSort(event.target.value as MachineExplorerSortColumn)}
            >
              {SORT_COLUMNS.map((column) => (
                <option key={column.value} value={column.value}>
                  {column.label}
                </option>
              ))}
            </select>
          </label>

          <div className="machine-explorer__field">
            <span className="machine-explorer__field-label">Direction</span>
            <button
              className="machine-explorer__button machine-explorer__button--soft"
              type="button"
              onClick={() => onSort(sort.column)}
            >
              {sort.direction === "asc" ? "Ascending ↑" : "Descending ↓"}
            </button>
          </div>
        </div>
      </div>

      <div className="machine-explorer__toolbar-actions">
        <button className="machine-explorer__button" type="button" onClick={onClearAll}>
          Clear All
        </button>
      </div>
    </section>
  );
}
