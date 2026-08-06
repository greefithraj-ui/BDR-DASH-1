import { Badge, Card } from "../../../components/design-system";
import type { MachineDetail } from "../machineExplorer.types";

type TimelinePlaceholderProps = {
  detail: MachineDetail;
};

export function TimelinePlaceholder({ detail }: TimelinePlaceholderProps) {
  const { timeline } = detail;

  return (
    <Card>
      <div className="machine-explorer-detail__section-header">
        <div>
          <p className="machine-explorer-detail__kicker">Timeline</p>
          <h2>Timeline</h2>
        </div>
        <Badge>Placeholder</Badge>
      </div>
      <ol className="machine-explorer-detail__timeline">
        {timeline.map((stage) => (
          <li
            key={stage.id}
            className={
              stage.reached
                ? "machine-explorer-detail__timeline-stage machine-explorer-detail__timeline-stage--reached"
                : "machine-explorer-detail__timeline-stage"
            }
          >
            <span className="machine-explorer-detail__timeline-dot" aria-hidden="true" />
            <div>
              <h3>{stage.name}</h3>
              <p>{stage.current ? "Current stage (mock)" : stage.note}</p>
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}
