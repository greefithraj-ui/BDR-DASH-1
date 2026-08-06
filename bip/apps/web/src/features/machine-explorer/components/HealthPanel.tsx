import { Badge, Card } from "../../../components/design-system";
import type { MachineDetail } from "../machineExplorer.types";

type HealthPanelProps = {
  detail: MachineDetail;
};

export function HealthPanel({ detail }: HealthPanelProps) {
  const { record, healthFactors } = detail;

  return (
    <Card>
      <div className="machine-explorer-detail__section-header">
        <div>
          <p className="machine-explorer-detail__kicker">Health</p>
          <h2>Health Panel</h2>
        </div>
        <Badge>Placeholder</Badge>
      </div>

      <div className="machine-explorer-detail__health-score">
        <strong>{record.healthScore}</strong>
        <span>/100</span>
      </div>

      <div className="machine-explorer-detail__health-factors">
        {healthFactors.map((factor) => (
          <div key={factor.label} className="machine-explorer-detail__health-factor">
            <span>{factor.label}</span>
            <Badge tone={factor.tone}>{factor.value}</Badge>
          </div>
        ))}
      </div>

      <div className="machine-explorer-detail__distribution">
        <div>
          <h3>Firmware Summary</h3>
          {record.firmwareSummary.map((item) => (
            <div key={item.firmware} className="machine-explorer-detail__distribution-row">
              <span>{item.firmware}</span>
              <strong>{item.count}</strong>
            </div>
          ))}
        </div>
        <div>
          <h3>Product Distribution</h3>
          {record.productDistribution.map((item) => (
            <div key={item.product} className="machine-explorer-detail__distribution-row">
              <span>{item.product}</span>
              <strong>{item.count}</strong>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
