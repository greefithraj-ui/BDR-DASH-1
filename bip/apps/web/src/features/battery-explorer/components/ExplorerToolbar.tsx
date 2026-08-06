import type { BatteryExplorerFilters, ExplorerOptions } from "../batteryExplorer.types";

type ExplorerToolbarProps = {
  filters: BatteryExplorerFilters;
  options: ExplorerOptions;
  onChange: (patch: Partial<BatteryExplorerFilters>) => void;
  onClearAll: () => void;
};

function SelectField({
  id,
  label,
  value,
  options,
  placeholder,
  onChange
}: {
  id: string;
  label: string;
  value: string;
  options: string[];
  placeholder: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="battery-explorer__field" htmlFor={id}>
      <span className="battery-explorer__field-label">{label}</span>
      <select id={id} className="battery-explorer__control" value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function TextField({
  id,
  label,
  value,
  placeholder,
  onChange
}: {
  id: string;
  label: string;
  value: string;
  placeholder: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="battery-explorer__field" htmlFor={id}>
      <span className="battery-explorer__field-label">{label}</span>
      <input
        id={id}
        className="battery-explorer__control"
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

export function ExplorerToolbar({ filters, options, onChange, onClearAll }: ExplorerToolbarProps) {
  return (
    <section className="battery-explorer__toolbar" aria-label="Battery explorer filters">
      <div className="battery-explorer__toolbar-group">
        <h2 className="battery-explorer__group-title">Search</h2>
        <div className="battery-explorer__toolbar-fields">
          <TextField
            id="explorer-serial"
            label="Serial Number"
            value={filters.serialNumberQuery}
            placeholder="e.g. RP-CH3-P18-WD-PG08-0001882"
            onChange={(value) => onChange({ serialNumberQuery: value })}
          />
          <TextField
            id="explorer-ring-mac"
            label="Ring MAC"
            value={filters.ringMacQuery}
            placeholder="e.g. A4:CF:12:..."
            onChange={(value) => onChange({ ringMacQuery: value })}
          />
          <TextField
            id="explorer-ring-name"
            label="Ring Name"
            value={filters.ringNameQuery}
            placeholder="e.g. Ring 14"
            onChange={(value) => onChange({ ringNameQuery: value })}
          />
        </div>
      </div>

      <div className="battery-explorer__toolbar-group">
        <h2 className="battery-explorer__group-title">Filters</h2>
        <div className="battery-explorer__toolbar-fields">
          <SelectField
            id="explorer-product"
            label="Product"
            value={filters.product}
            options={options.products}
            placeholder="All products"
            onChange={(value) => onChange({ product: value })}
          />
          <SelectField
            id="explorer-machine"
            label="Machine"
            value={filters.machine}
            options={options.machines}
            placeholder="All machines"
            onChange={(value) => onChange({ machine: value })}
          />
          <SelectField
            id="explorer-slot"
            label="Slot"
            value={filters.slot}
            options={options.slots}
            placeholder="All slots"
            onChange={(value) => onChange({ slot: value })}
          />
          <SelectField
            id="explorer-state"
            label="State"
            value={filters.state}
            options={options.states}
            placeholder="All states"
            onChange={(value) => onChange({ state: value })}
          />
          <SelectField
            id="explorer-firmware"
            label="Firmware"
            value={filters.firmware}
            options={options.firmwares}
            placeholder="All firmware"
            onChange={(value) => onChange({ firmware: value })}
          />
        </div>
      </div>

      <div className="battery-explorer__toolbar-group">
        <h2 className="battery-explorer__group-title">Date Range</h2>
        <div className="battery-explorer__toolbar-fields">
          <label className="battery-explorer__field" htmlFor="explorer-date-from">
            <span className="battery-explorer__field-label">From</span>
            <input
              id="explorer-date-from"
              className="battery-explorer__control"
              type="date"
              value={filters.dateFrom}
              onChange={(event) => onChange({ dateFrom: event.target.value })}
            />
          </label>
          <label className="battery-explorer__field" htmlFor="explorer-date-to">
            <span className="battery-explorer__field-label">To</span>
            <input
              id="explorer-date-to"
              className="battery-explorer__control"
              type="date"
              value={filters.dateTo}
              onChange={(event) => onChange({ dateTo: event.target.value })}
            />
          </label>
          <div className="battery-explorer__toolbar-actions">
            <button className="battery-explorer__button" type="button" onClick={onClearAll}>
              Clear All
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
