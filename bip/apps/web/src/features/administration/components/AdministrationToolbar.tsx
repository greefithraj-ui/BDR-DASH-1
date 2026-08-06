import type { AdministrationFilters, AdministrationOptions } from "../administration.types";

type AdministrationToolbarProps = {
  filters: AdministrationFilters;
  options: AdministrationOptions;
  onClearAll: () => void;
  onFiltersChange: (patch: Partial<AdministrationFilters>) => void;
};

export function AdministrationToolbar({ filters, options, onClearAll, onFiltersChange }: AdministrationToolbarProps) {
  return (
    <section className="administration__toolbar" aria-label="Administration filters">
      <div className="administration__toolbar-group">
        <h2 className="administration__group-title">Search</h2>
        <div className="administration__toolbar-fields">
          <label className="administration__field" htmlFor="admin-search">
            <span className="administration__field-label">Search</span>
            <input
              id="admin-search"
              className="administration__control"
              type="text"
              value={filters.search}
              placeholder="Machine ID, name, firmware, collector…"
              onChange={(event) => onFiltersChange({ search: event.target.value })}
            />
          </label>
        </div>
      </div>

      <div className="administration__toolbar-group">
        <h2 className="administration__group-title">Filters</h2>
        <div className="administration__toolbar-fields">
          <label className="administration__field" htmlFor="admin-status">
            <span className="administration__field-label">Status</span>
            <select
              id="admin-status"
              className="administration__control"
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

          <label className="administration__field" htmlFor="admin-connection">
            <span className="administration__field-label">Connection</span>
            <select
              id="admin-connection"
              className="administration__control"
              value={filters.connection}
              onChange={(event) => onFiltersChange({ connection: event.target.value })}
            >
              <option value="">All connections</option>
              {options.connections.map((connection) => (
                <option key={connection} value={connection}>
                  {connection}
                </option>
              ))}
            </select>
          </label>

          <div className="administration__toolbar-actions">
            <button className="administration__button" type="button" onClick={onClearAll}>
              Clear All
            </button>
          </div>
        </div>
      </div>

      <div className="administration__toolbar-group">
        <h2 className="administration__group-title">Last Seen</h2>
        <div className="administration__toolbar-fields">
          <label className="administration__field" htmlFor="admin-from">
            <span className="administration__field-label">From</span>
            <input
              id="admin-from"
              className="administration__control"
              type="date"
              value={filters.fromDate}
              onChange={(event) => onFiltersChange({ fromDate: event.target.value })}
            />
          </label>
          <label className="administration__field" htmlFor="admin-to">
            <span className="administration__field-label">To</span>
            <input
              id="admin-to"
              className="administration__control"
              type="date"
              value={filters.toDate}
              onChange={(event) => onFiltersChange({ toDate: event.target.value })}
            />
          </label>
        </div>
      </div>
    </section>
  );
}
