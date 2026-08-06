import type { ReportsFilters, ReportsOptions } from "../reports.types";

type ReportsToolbarProps = {
  filters: ReportsFilters;
  options: ReportsOptions;
  onFiltersChange: (patch: Partial<ReportsFilters>) => void;
  onClearAll: () => void;
};

export function ReportsToolbar({ filters, options, onFiltersChange, onClearAll }: ReportsToolbarProps) {
  return (
    <section className="reports__toolbar" aria-label="Reports filters">
      <div className="reports__toolbar-group">
        <h2 className="reports__group-title">Search</h2>
        <div className="reports__toolbar-fields">
          <label className="reports__field" htmlFor="reports-search">
            <span className="reports__field-label">Search</span>
            <input
              id="reports-search"
              className="reports__control"
              type="text"
              value={filters.search}
              placeholder="Title, description, category, owner…"
              onChange={(event) => onFiltersChange({ search: event.target.value })}
            />
          </label>
        </div>
      </div>

      <div className="reports__toolbar-group">
        <h2 className="reports__group-title">Filters</h2>
        <div className="reports__toolbar-fields">
          <label className="reports__field" htmlFor="reports-category">
            <span className="reports__field-label">Category</span>
            <select
              id="reports-category"
              className="reports__control"
              value={filters.category}
              onChange={(event) => onFiltersChange({ category: event.target.value })}
            >
              <option value="">All categories</option>
              {options.categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>

          <label className="reports__field" htmlFor="reports-status">
            <span className="reports__field-label">Status</span>
            <select
              id="reports-status"
              className="reports__control"
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

          <label className="reports__field" htmlFor="reports-owner">
            <span className="reports__field-label">Owner</span>
            <select
              id="reports-owner"
              className="reports__control"
              value={filters.owner}
              onChange={(event) => onFiltersChange({ owner: event.target.value })}
            >
              <option value="">All owners</option>
              {options.owners.map((owner) => (
                <option key={owner} value={owner}>
                  {owner}
                </option>
              ))}
            </select>
          </label>

          <label className="reports__field" htmlFor="reports-frequency">
            <span className="reports__field-label">Frequency</span>
            <select
              id="reports-frequency"
              className="reports__control"
              value={filters.frequency}
              onChange={(event) => onFiltersChange({ frequency: event.target.value })}
            >
              <option value="">All frequencies</option>
              {options.frequencies.map((frequency) => (
                <option key={frequency} value={frequency}>
                  {frequency}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="reports__toolbar-group">
        <h2 className="reports__group-title">Date Range</h2>
        <div className="reports__toolbar-fields">
          <label className="reports__field" htmlFor="reports-date-from">
            <span className="reports__field-label">Last Run From</span>
            <input
              id="reports-date-from"
              className="reports__control"
              type="date"
              value={filters.dateFrom}
              onChange={(event) => onFiltersChange({ dateFrom: event.target.value })}
            />
          </label>
          <label className="reports__field" htmlFor="reports-date-to">
            <span className="reports__field-label">Last Run To</span>
            <input
              id="reports-date-to"
              className="reports__control"
              type="date"
              value={filters.dateTo}
              onChange={(event) => onFiltersChange({ dateTo: event.target.value })}
            />
          </label>
          <div className="reports__toolbar-actions">
            <button className="reports__button" type="button" onClick={onClearAll}>
              Clear All
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
