import { Badge, Card } from "../../../components/design-system";
import type { LifecycleStageDetail } from "../batteryExplorer.types";

type DetailLifecycleTimelineProps = {
  stages: LifecycleStageDetail[];
};

export function DetailLifecycleTimeline({ stages }: DetailLifecycleTimelineProps) {
  return (
    <Card>
      <div className="battery-explorer-detail__section-header">
        <div>
          <p className="battery-explorer-detail__kicker">Lifecycle</p>
          <h2>Lifecycle Timeline</h2>
        </div>
        <Badge>Placeholder</Badge>
      </div>
      <ol className="battery-explorer-detail__timeline">
        {stages.map((stage) => (
          <li
            key={stage.id}
            className={
              stage.reached
                ? "battery-explorer-detail__timeline-stage battery-explorer-detail__timeline-stage--reached"
                : "battery-explorer-detail__timeline-stage"
            }
          >
            <span className="battery-explorer-detail__timeline-dot" aria-hidden="true" />
            <div>
              <h3>{stage.name}</h3>
              <p>{stage.current ? "Current stage" : stage.note}</p>
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}
