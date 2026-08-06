import { Badge } from "../../../components/design-system";
import { getConnectionTone, getMachineTone } from "../administration.mock";
import type { MachineRecord } from "../administration.types";

type AdministrationTableProps = {
  machines: MachineRecord[];
  onSelect: (machine: MachineRecord) => void;
};

export function AdministrationTable({ machines, onSelect }: AdministrationTableProps) {
  return (
    <div className="administration__table-scroll">
      <table className="administration__table">
        <thead>
          <tr>
            <th scope="col">Machine ID</th>
            <th scope="col">Machine Name</th>
            <th scope="col">Status</th>
            <th scope="col">Last Seen</th>
            <th scope="col">Collector</th>
            <th scope="col">Health</th>
            <th scope="col">Firmware</th>
            <th scope="col">Connection</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {machines.map((machine) => (
            <tr key={machine.id} className="administration__row" onClick={() => onSelect(machine)}>
              <td className="administration__strong">{machine.machineId}</td>
              <td>{machine.machineName}</td>
              <td>
                <Badge tone={getMachineTone(machine)}>{machine.status}</Badge>
              </td>
              <td>{machine.lastSeen}</td>
              <td>{machine.collectorVersion}</td>
              <td>{machine.healthScore}</td>
              <td>{machine.firmware}</td>
              <td>
                <Badge tone={getConnectionTone(machine)}>{machine.connection}</Badge>
              </td>
              <td>
                <button
                  className="administration__button"
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    onSelect(machine);
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
