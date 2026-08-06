import { Badge, Card } from "../../../components/design-system";
import type { MachineDetail } from "../machineExplorer.types";

type BatteryListProps = {
  detail: MachineDetail;
};

export function BatteryList({ detail }: BatteryListProps) {
  const { batteryList } = detail;

  return (
    <Card>
      <div className="machine-explorer-detail__section-header">
        <div>
          <p className="machine-explorer-detail__kicker">Batteries</p>
          <h2>Battery List</h2>
        </div>
        <Badge tone="info">{batteryList.length} batteries registered</Badge>
      </div>
      <div className="machine-explorer-detail__table-scroll">
        <table className="machine-explorer-detail__table">
          <thead>
            <tr>
              <th scope="col">Serial Number</th>
              <th scope="col">Slot</th>
              <th scope="col">Current State</th>
              <th scope="col">Firmware</th>
              <th scope="col">Last Seen</th>
            </tr>
          </thead>
          <tbody>
            {batteryList.map((battery) => (
              <tr key={battery.id}>
                <td className="machine-explorer-detail__mono">{battery.serialNumber}</td>
                <td>{battery.slot}</td>
                <td>
                  <Badge tone={battery.tone}>{battery.currentState}</Badge>
                </td>
                <td>{battery.firmware}</td>
                <td>{battery.lastSeen}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
