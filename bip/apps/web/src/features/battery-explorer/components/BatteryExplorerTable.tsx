import { Badge, EmptyState } from "../../../components/design-system";
import type { BatteryRecord, ExplorerSort, ExplorerSortColumn } from "../batteryExplorer.types";

type BatteryExplorerTableProps = {
  records: BatteryRecord[];
  sort: ExplorerSort;
  onSort: (column: ExplorerSortColumn) => void;
  onSelect: (record: BatteryRecord) => void;
};

const COLUMNS: { key: keyof BatteryRecord | "actions"; label: string; sortable: boolean }[] = [
  { key: "serialNumber", label: "Serial Number", sortable: true },
  { key: "ringMac", label: "Ring MAC", sortable: false },
  { key: "ringName", label: "Ring Name", sortable: true },
  { key: "product", label: "Product", sortable: true },
  { key: "machine", label: "Machine", sortable: true },
  { key: "slot", label: "Slot", sortable: false },
  { key: "currentState", label: "Current State", sortable: true },
  { key: "firmware", label: "Firmware", sortable: true },
  { key: "firstSeen", label: "First Seen", sortable: true },
  { key: "lastSeen", label: "Last Seen", sortable: true },
  { key: "lifecycleStatus", label: "Lifecycle Status", sortable: false },
  { key: "actions", label: "Actions", sortable: false }
];

export function BatteryExplorerTable({ records, sort, onSort, onSelect }: BatteryExplorerTableProps) {
  if (records.length === 0) {
    return <EmptyState label="No batteries match the current filters" />;
  }

  return (
    <div className="battery-explorer__table-scroll">
      <table className="battery-explorer__table">
        <thead>
          <tr>
            {COLUMNS.map((column) => (
              <th key={column.key} scope="col">
                {column.sortable ? (
                  <button
                    className="battery-explorer__sort-button"
                    type="button"
                    onClick={() => onSort(column.key as ExplorerSortColumn)}
                  >
                    {column.label}
                    {sort.column === column.key ? (
                      <span className="battery-explorer__sort-indicator">
                        {sort.direction === "asc" ? " ↑" : " ↓"}
                      </span>
                    ) : null}
                  </button>
                ) : (
                  column.label
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr key={record.id} className="battery-explorer__row" onClick={() => onSelect(record)}>
              <td className="battery-explorer__serial">{record.serialNumber}</td>
              <td className="battery-explorer__mono">{record.ringMac}</td>
              <td>{record.ringName}</td>
              <td>{record.product}</td>
              <td>{record.machine}</td>
              <td>{record.slot}</td>
              <td>
                <Badge tone={record.tone}>{record.currentState}</Badge>
              </td>
              <td>{record.firmware}</td>
              <td>{record.firstSeen}</td>
              <td>{record.lastSeen}</td>
              <td>{record.lifecycleStatus}</td>
              <td>
                <button
                  className="battery-explorer__button"
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    onSelect(record);
                  }}
                >
                  View
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
