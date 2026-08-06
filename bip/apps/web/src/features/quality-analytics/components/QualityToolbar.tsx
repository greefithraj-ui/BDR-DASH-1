import type { QualityFilters, QualityOptions } from "../qualityAnalytics.types";

type QualityToolbarProps = {
  filters: QualityFilters;
  options: QualityOptions;
  onFiltersChange: (patch: Partial<QualityFilters>) => void;
  onClearAll: () => void;
};

export function QualityToolbar({ filters, options, onFiltersChange, onClearAll }: QualityToolbarProps) {
  return (
    <section className="quality-analytics__toolbar" aria-label="Quality analytics filters">
      <div className="quality-analytics__toolbar-group">
        <h2 className="quality-analytics__group-title">Search</h2>
        <div className="quality-analytics__toolbar-fields">
          <label className="quality-analytics__field" htmlFor="quality-search">
            <span className="quality-analytics__field-label">Search</span>
            <input
              id="quality-search"
              className="quality-analytics__control"
              type="text"
              value={filters.search}
              placeholder="Product, category, machine, firmware…"
              onChange={(event) => onFiltersChange({ search: event.target.value })}
            />
          </label>
        </div>
      </div>

      <div className="quality-analytics__toolbar-group">
        <h2 className="quality-analytics__group-title">Filters</h2>
        <div className="quality-analytics__toolbar-fields">
          <label className="quality-analytics__field" htmlFor="quality-product">
            <span className="quality-analytics__field-label">Product</span>
            <select
              id="quality-product"
              className="quality-analytics__control"
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

          <label className="quality-analytics__field" htmlFor="quality-machine">
            <span className="quality-analytics__field-label">Machine</span>
            <select
              id="quality-machine"
              className="quality-analytics__control"
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

          <label className="quality-analytics__field" htmlFor="quality-firmware">
            <span className="quality-analytics__field-label">Firmware</span>
            <select
              id="quality-firmware"
              className="quality-analytics__control"
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

          <label className="quality-analytics__field" htmlFor="quality-result">
            <span className="quality-analytics__field-label">Pass/Fail</span>
            <select
              id="quality-result"
              className="quality-analytics__control"
              value={filters.result}
              onChange={(event) => onFiltersChange({ result: event.target.value })}
            >
              <option value="">All results</option>
              {options.results.map((result) => (
                <option key={result} value={result}>
                  {result}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="quality-analytics__toolbar-group">
        <h2 className="quality-analytics__group-title">Date Range</h2>
        <div className="quality-analytics__toolbar-fields">
          <label className="quality-analytics__field" htmlFor="quality-date-from">
            <span className="quality-analytics__field-label">From</span>
            <input
              id="quality-date-from"
              className="quality-analytics__control"
              type="date"
              value={filters.dateFrom}
              onChange={(event) => onFiltersChange({ dateFrom: event.target.value })}
            />
          </label>
          <label className="quality-analytics__field" htmlFor="quality-date-to">
            <span className="quality-analytics__field-label">To</span>
            <input
              id="quality-date-to"
              className="quality-analytics__control"
              type="date"
              value={filters.dateTo}
              onChange={(event) => onFiltersChange({ dateTo: event.target.value })}
            />
          </label>
          <div className="quality-analytics__toolbar-actions">
            <button className="quality-analytics__button" type="button" onClick={onClearAll}>
              Clear All
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
