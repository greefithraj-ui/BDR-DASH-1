import type { PerformanceFilters, PerformanceOptions } from "../performanceAnalytics.types";

type PerformanceToolbarProps = {
  filters: PerformanceFilters;
  options: PerformanceOptions;
  onFiltersChange: (patch: Partial<PerformanceFilters>) => void;
  onClearAll: () => void;
};

export function PerformanceToolbar({ filters, options, onFiltersChange, onClearAll }: PerformanceToolbarProps) {
  return (
    <section className="performance-analytics__toolbar" aria-label="Performance analytics filters">
      <div className="performance-analytics__toolbar-group">
        <h2 className="performance-analytics__group-title">Search</h2>
        <div className="performance-analytics__toolbar-fields">
          <label className="performance-analytics__field" htmlFor="performance-search">
            <span className="performance-analytics__field-label">Search</span>
            <input
              id="performance-search"
              className="performance-analytics__control"
              type="text"
              value={filters.search}
              placeholder="Machine, product, category, firmware…"
              onChange={(event) => onFiltersChange({ search: event.target.value })}
            />
          </label>
        </div>
      </div>

      <div className="performance-analytics__toolbar-group">
        <h2 className="performance-analytics__group-title">Filters</h2>
        <div className="performance-analytics__toolbar-fields">
          <label className="performance-analytics__field" htmlFor="performance-machine">
            <span className="performance-analytics__field-label">Machine</span>
            <select
              id="performance-machine"
              className="performance-analytics__control"
              value={filters.machine}
              onChange={(event) => onFiltersChange({ machine: event.target.value })}
            >
              <option value="">All machines</option>
              {options.machines.map((machine) => (
                <option key={machine} value={machine}>
                  {machine}
                </option>
              ))}
            </select>
          </label>

          <label className="performance-analytics__field" htmlFor="performance-product">
            <span className="performance-analytics__field-label">Product</span>
            <select
              id="performance-product"
              className="performance-analytics__control"
              value={filters.product}
              onChange={(event) => onFiltersChange({ product: event.target.value })}
            >
              <option value="">All products</option>
              {options.products.map((product) => (
                <option key={product} value={product}>
                  {product}
                </option>
              ))}
            </select>
          </label>

          <label className="performance-analytics__field" htmlFor="performance-firmware">
            <span className="performance-analytics__field-label">Firmware</span>
            <select
              id="performance-firmware"
              className="performance-analytics__control"
              value={filters.firmware}
              onChange={(event) => onFiltersChange({ firmware: event.target.value })}
            >
              <option value="">All firmware</option>
              {options.firmwares.map((firmware) => (
                <option key={firmware} value={firmware}>
                  {firmware}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="performance-analytics__toolbar-group">
        <h2 className="performance-analytics__group-title">Date Range</h2>
        <div className="performance-analytics__toolbar-fields">
          <label className="performance-analytics__field" htmlFor="performance-date-from">
            <span className="performance-analytics__field-label">From</span>
            <input
              id="performance-date-from"
              className="performance-analytics__control"
              type="date"
              value={filters.dateFrom}
              onChange={(event) => onFiltersChange({ dateFrom: event.target.value })}
            />
          </label>
          <label className="performance-analytics__field" htmlFor="performance-date-to">
            <span className="performance-analytics__field-label">To</span>
            <input
              id="performance-date-to"
              className="performance-analytics__control"
              type="date"
              value={filters.dateTo}
              onChange={(event) => onFiltersChange({ dateTo: event.target.value })}
            />
          </label>
          <div className="performance-analytics__toolbar-actions">
            <button className="performance-analytics__button" type="button" onClick={onClearAll}>
              Clear All
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
