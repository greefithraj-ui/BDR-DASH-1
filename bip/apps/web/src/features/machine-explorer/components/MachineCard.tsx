import type { MachineRecord, MachineStatus, MachineTone } from "../machineExplorer.types";

type StatusIndicatorProps = {
  status: MachineStatus;
};

export function StatusIndicator({ status }: StatusIndicatorProps) {
  const online = status === "Online";

  return (
    <span className={online ? "machine-explorer__status machine-explorer__status--online" : "machine-explorer__status machine-explorer__status--offline"}>
      <span className="machine-explorer__status-dot" aria-hidden="true" />
      {status}
    </span>
  );
}

function healthTone(score: number): MachineTone {
  if (score >= 80) {
    return "success";
  }

  if (score >= 60) {
    return "info";
  }

  return "danger";
}

type MachineCardProps = {
  machine: MachineRecord;
  onSelect: (machine: MachineRecord) => void;
};

export function MachineCard({ machine, onSelect }: MachineCardProps) {
  const occupancyPercent = Math.round((machine.slotsOccupied / machine.slotCount) * 100);
  const scoreTone = healthTone(machine.healthScore);

  return (
    <article
      className="machine-explorer__card"
      role="button"
      tabIndex={0}
      onClick={() => onSelect(machine)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onSelect(machine);
        }
      }}
    >
      <header className="machine-explorer__card-header">
        <div>
          <h2>{machine.machineId}</h2>
          <p>{machine.name}</p>
        </div>
        <StatusIndicator status={machine.status} />
      </header>

      <div className="machine-explorer__health">
        <div className="machine-explorer__health-heading">
          <span>Health Score</span>
          <strong>{machine.healthScore}/100</strong>
        </div>
        <div className="machine-explorer__health-track" aria-hidden="true">
          <div
            className={`machine-explorer__health-fill machine-explorer__health-fill--${scoreTone}`}
            style={{ width: `${machine.healthScore}%` }}
          />
        </div>
      </div>

      <div className="machine-explorer__card-metrics">
        <div className="machine-explorer__card-metric">
          <strong>{machine.activeBatteries}</strong>
          <span>Active</span>
        </div>
        <div className="machine-explorer__card-metric">
          <strong>{machine.pendingRemovalCount}</strong>
          <span>Pending Removal</span>
        </div>
        <div className="machine-explorer__card-metric">
          <strong>{machine.finalizedCount}</strong>
          <span>Finalized</span>
        </div>
      </div>

      <div className="machine-explorer__occupancy">
        <div className="machine-explorer__occupancy-heading">
          <span>Slot Occupancy</span>
          <strong>
            {machine.slotsOccupied}/{machine.slotCount}
          </strong>
        </div>
        <div className="machine-explorer__occupancy-track" aria-hidden="true">
          <div className="machine-explorer__occupancy-fill" style={{ width: `${occupancyPercent}%` }} />
        </div>
      </div>

      <footer className="machine-explorer__card-footer">
        <span>FW {machine.dominantFirmware}</span>
        <span>Last seen {machine.lastSeen}</span>
      </footer>
    </article>
  );
}
