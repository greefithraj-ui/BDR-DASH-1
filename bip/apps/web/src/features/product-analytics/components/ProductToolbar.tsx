import type { ProductFilters, ProductOptions } from "../productAnalytics.types";

type ProductToolbarProps = {
  filters: ProductFilters;
  options: ProductOptions;
  onFiltersChange: (patch: Partial<ProductFilters>) => void;
  onClearAll: () => void;
};

export function ProductToolbar({ filters, options, onFiltersChange, onClearAll }: ProductToolbarProps) {
  return (
    <section className="product-analytics__toolbar" aria-label="Product analytics filters">
      <div className="product-analytics__toolbar-group">
        <h2 className="product-analytics__group-title">Search</h2>
        <div className="product-analytics__toolbar-fields">
          <label className="product-analytics__field" htmlFor="product-search">
            <span className="product-analytics__field-label">Search</span>
            <input
              id="product-search"
              className="product-analytics__control"
              type="text"
              value={filters.search}
              placeholder="Product, category, description…"
              onChange={(event) => onFiltersChange({ search: event.target.value })}
            />
          </label>
        </div>
      </div>

      <div className="product-analytics__toolbar-group">
        <h2 className="product-analytics__group-title">Filters</h2>
        <div className="product-analytics__toolbar-fields">
          <label className="product-analytics__field" htmlFor="product-filter">
            <span className="product-analytics__field-label">Product</span>
            <select
              id="product-filter"
              className="product-analytics__control"
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

          <label className="product-analytics__field" htmlFor="product-firmware">
            <span className="product-analytics__field-label">Firmware</span>
            <select
              id="product-firmware"
              className="product-analytics__control"
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

          <label className="product-analytics__field" htmlFor="product-machine">
            <span className="product-analytics__field-label">Machine</span>
            <select
              id="product-machine"
              className="product-analytics__control"
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

          <label className="product-analytics__field" htmlFor="product-lifecycle">
            <span className="product-analytics__field-label">Lifecycle State</span>
            <select
              id="product-lifecycle"
              className="product-analytics__control"
              value={filters.lifecycleState}
              onChange={(event) => onFiltersChange({ lifecycleState: event.target.value })}
            >
              <option value="">All states</option>
              {options.lifecycleStates.map((state) => (
                <option key={state} value={state}>
                  {state}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="product-analytics__toolbar-group">
        <h2 className="product-analytics__group-title">Date Range</h2>
        <div className="product-analytics__toolbar-fields">
          <label className="product-analytics__field" htmlFor="product-date-from">
            <span className="product-analytics__field-label">From</span>
            <input
              id="product-date-from"
              className="product-analytics__control"
              type="date"
              value={filters.dateFrom}
              onChange={(event) => onFiltersChange({ dateFrom: event.target.value })}
            />
          </label>
          <label className="product-analytics__field" htmlFor="product-date-to">
            <span className="product-analytics__field-label">To</span>
            <input
              id="product-date-to"
              className="product-analytics__control"
              type="date"
              value={filters.dateTo}
              onChange={(event) => onFiltersChange({ dateTo: event.target.value })}
            />
          </label>
          <div className="product-analytics__toolbar-actions">
            <button className="product-analytics__button" type="button" onClick={onClearAll}>
              Clear All
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
