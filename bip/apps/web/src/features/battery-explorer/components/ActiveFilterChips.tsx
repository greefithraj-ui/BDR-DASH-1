import type { BatteryExplorerFilters } from "../batteryExplorer.types";

type ActiveFilterChipsProps = {
  filters: BatteryExplorerFilters;
  onRemove: (key: keyof BatteryExplorerFilters) => void;
  onClearAll: () => void;
};

const CHIP_DEFINITIONS: { key: keyof BatteryExplorerFilters; label: string }[] = [
  { key: "serialNumberQuery", label: "Serial" },
  { key: "ringMacQuery", label: "Ring MAC" },
  { key: "ringNameQuery", label: "Ring Name" },
  { key: "product", label: "Product" },
  { key: "machine", label: "Machine" },
  { key: "slot", label: "Slot" },
  { key: "state", label: "State" },
  { key: "firmware", label: "Firmware" },
  { key: "dateFrom", label: "From" },
  { key: "dateTo", label: "To" }
];

function buildChips(filters: BatteryExplorerFilters): { key: keyof BatteryExplorerFilters; value: string; label: string }[] {
  return CHIP_DEFINITIONS.flatMap((definition) => {
    const value = filters[definition.key].trim();
    if (!value) {
      return [];
    }

    return [{ key: definition.key, value, label: `${definition.label}: ${value}` }];
  });
}

export function ActiveFilterChips({ filters, onRemove, onClearAll }: ActiveFilterChipsProps) {
  const chips = buildChips(filters);

  if (chips.length === 0) {
    return null;
  }

  return (
    <section className="battery-explorer__chips" aria-label="Active filters">
      {chips.map((chip) => (
        <span key={chip.key} className="battery-explorer__chip">
          {chip.label}
          <button
            className="battery-explorer__chip-remove"
            type="button"
            aria-label={`Remove ${chip.label}`}
            onClick={() => onRemove(chip.key)}
          >
            ×
          </button>
        </span>
      ))}
      <button className="battery-explorer__chip-clear" type="button" onClick={onClearAll}>
        Clear all
      </button>
    </section>
  );
}
