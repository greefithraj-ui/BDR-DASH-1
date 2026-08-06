import { Badge, Card } from "../../../components/design-system";
import type { MachineDetail, SlotOccupancySlot } from "../machineExplorer.types";

type SlotOverviewProps = {
  detail: MachineDetail;
};

function SlotCell({ slot }: { slot: SlotOccupancySlot }) {
  if (!slot.occupied) {
    return (
      <div className="machine-explorer-detail__slot machine-explorer-detail__slot--empty">
        <strong>{slot.slot}</strong>
        <span>Empty</span>
      </div>
    );
  }

  return (
    <div className="machine-explorer-detail__slot machine-explorer-detail__slot--occupied">
      <strong>{slot.slot}</strong>
      <span className="machine-explorer-detail__slot-serial">{slot.serialNumber}</span>
      <Badge tone={slot.tone}>{slot.currentState}</Badge>
    </div>
  );
}

export function SlotOverview({ detail }: SlotOverviewProps) {
  const { record, slotOverview } = detail;
  const occupiedCount = slotOverview.filter((slot) => slot.occupied).length;

  return (
    <Card>
      <div className="machine-explorer-detail__section-header">
        <div>
          <p className="machine-explorer-detail__kicker">Slots</p>
          <h2>Slot Overview</h2>
        </div>
        <Badge>Placeholder</Badge>
      </div>
      <p className="machine-explorer-detail__section-note">
        {occupiedCount} of {record.slotCount} slots occupied · placeholder overview, real layout arrives in a later phase.
      </p>
      <div className="machine-explorer-detail__slot-grid">
        {slotOverview.map((slot) => (
          <SlotCell key={slot.slot} slot={slot} />
        ))}
      </div>
    </Card>
  );
}
