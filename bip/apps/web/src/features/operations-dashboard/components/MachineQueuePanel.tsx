import { useNavigate } from "react-router-dom";
import { Badge, Card } from "../../../components/design-system";
import type { MachineQueueItem } from "../useOperationsDashboard";

type MachineQueuePanelProps = {
  machines: MachineQueueItem[];
};

export function MachineQueuePanel({ machines }: MachineQueuePanelProps) {
  const navigate = useNavigate();

  const handleRowClick = (machineId: string) => {
    navigate(`/machine-explorer?machineId=${encodeURIComponent(machineId)}`);
  };

  return (
    <Card className="ops-machines-card">
      <div className="ops-panel-header">
        <h2>LIVE MACHINE WORKLOAD & QUEUES</h2>
        <span className="ops-panel-subtitle">Click row to inspect machine station</span>
      </div>

      <div className="ops-table-wrapper">
        <table className="ops-table">
          aria-label="Live machine queues"
          <thead>
            <tr>
              <th>Machine</th>
              <th>Status</th>
              <th>Active Ring</th>
              <th>Queue Length</th>
              <th>Wait Time</th>
            </tr>
          </thead>
          <tbody>
            {machines.map((m) => (
              <tr
                key={m.id}
                onClick={() => handleRowClick(m.id)}
                className="ops-table-row ops-table-row--clickable"
                title={`Click to view ${m.machineName}`}
              >
                <td className="ops-cell--bold">{m.machineName}</td>
                <td>
                  <Badge tone={m.tone}>{m.status}</Badge>
                </td>
                <td className="ops-cell--monospace">{m.activeRingId}</td>
                <td>{m.queueLength} Rings</td>
                <td>{m.waitTime}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
