import { Badge, Card } from "../../../components/design-system";
import type { MachineRecord } from "../administration.types";
import { AdministrationTable } from "./AdministrationTable";

type MachineRegistryPanelProps = {
  machines: MachineRecord[];
  onSelect: (machine: MachineRecord) => void;
};

export function MachineRegistryPanel({ machines, onSelect }: MachineRegistryPanelProps) {
  return (
    <Card>
      <div className="administration__section-header">
        <div>
          <p className="administration__kicker">Registry</p>
          <h2>Machine Registry</h2>
        </div>
        <Badge tone="info">{machines.length} machines</Badge>
      </div>
      <AdministrationTable machines={machines} onSelect={onSelect} />
    </Card>
  );
}
