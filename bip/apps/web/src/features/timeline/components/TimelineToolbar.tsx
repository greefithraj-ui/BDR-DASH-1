import type {
  TimelineFilters,
  TimelineGroupBy,
  TimelineOptions,
  TimelineSort
} from "../timeline.types";

type TimelineToolbarProps = {
  filters: TimelineFilters;
  options: TimelineOptions;
  groupBy: TimelineGroupBy;
  sort: TimelineSort;
  onFiltersChange: (patch: Partial<TimelineFilters>) => void;
  onClearAll: () => void;
  onGroupByChange: (groupBy: TimelineGroupBy) => void;
  onToggleSort: () => void;
};

const GROUP_BY_OPTIONS: { value: TimelineGroupBy; label: string }[] = [
  { value: "date", label: "Date" },
  { value: "machine", label: "Machine" },
  { value: "battery", label: "Battery" }
];

export function TimelineToolbar({
  filters,
  options,
  groupBy,
  sort,
  onFiltersChange,
  onClearAll,
  onGroupByChange,
  onToggleSort
}: TimelineToolbarProps) {
  return (
    <section className="timeline__toolbar" aria-label="Timeline filters">
      <div className="timeline__toolbar-group">
        <h2 className="timeline__group-title">Search</h2>
        <div className="timeline__toolbar-fields">
          <label className="timeline__field" htmlFor="timeline-search">
            <span className="timeline__field-label">Search</span>
            <input
              id="timeline-search"
              className="timeline__control"
              type="text"
              value={filters.search}
              placeholder="Event, battery, machine, slot, reason…"
              onChange={(event) => onFiltersChange({ search: event.target.value })}
            />
          </label>
        </div>
      </div>

      <div className="timeline__toolbar-group">
        <h2 className="timeline__group-title">Filters</h2>
        <div className="timeline__toolbar-fields">
          <label className="timeline__field" htmlFor="timeline-machine">
            <span className="timeline__field-label">Machine</span>
            <select
              id="timeline-machine"
              className="timeline__control"
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

          <label className="timeline__field" htmlFor="timeline-battery">
            <span className="timeline__field-label">Battery</span>
            <select
              id="timeline-battery"
              className="timeline__control"
              value={filters.battery}
              onChange={(event) => onFiltersChange({ battery: event.target.value })}
            >
              <option value="">All batteries</option>
              {options.batteries.map((battery) => (
                <option key={battery} value={battery}>
                  {battery}
                </option>
              ))}
            </select>
          </label>

          <label className="timeline__field" htmlFor="timeline-event-type">
            <span className="timeline__field-label">Event Type</span>
            <select
              id="timeline-event-type"
              className="timeline__control"
              value={filters.eventType}
              onChange={(event) => onFiltersChange({ eventType: event.target.value })}
            >
              <option value="">All event types</option>
              {options.eventTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="timeline__toolbar-group">
        <h2 className="timeline__group-title">Date Range</h2>
        <div className="timeline__toolbar-fields">
          <label className="timeline__field" htmlFor="timeline-date-from">
            <span className="timeline__field-label">From</span>
            <input
              id="timeline-date-from"
              className="timeline__control"
              type="date"
              value={filters.dateFrom}
              onChange={(event) => onFiltersChange({ dateFrom: event.target.value })}
            />
          </label>
          <label className="timeline__field" htmlFor="timeline-date-to">
            <span className="timeline__field-label">To</span>
            <input
              id="timeline-date-to"
              className="timeline__control"
              type="date"
              value={filters.dateTo}
              onChange={(event) => onFiltersChange({ dateTo: event.target.value })}
            />
          </label>
          <div className="timeline__field">
            <span className="timeline__field-label">Direction</span>
            <button className="timeline__button timeline__button--soft" type="button" onClick={onToggleSort}>
              {sort.direction === "desc" ? "Newest first ↓" : "Oldest first ↑"}
            </button>
          </div>
        </div>
      </div>

      <div className="timeline__toolbar-group">
        <h2 className="timeline__group-title">Group By</h2>
        <div className="timeline__toolbar-fields timeline__toolbar-fields--segmented">
          <div className="timeline__segmented" role="group" aria-label="Group by">
            {GROUP_BY_OPTIONS.map((option) => (
              <button
                key={option.value}
                className={groupBy === option.value ? "timeline__segment timeline__segment--active" : "timeline__segment"}
                type="button"
                onClick={() => onGroupByChange(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
          <div className="timeline__toolbar-actions">
            <button className="timeline__button" type="button" onClick={onClearAll}>
              Clear All
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
