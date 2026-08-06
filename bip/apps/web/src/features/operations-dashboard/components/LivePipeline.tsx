import { Badge, Card } from "../../../components/design-system";
import type { PipelineStage } from "../useOperationsDashboard";

type LivePipelineProps = {
  stages: PipelineStage[];
};

export function LivePipeline({ stages }: LivePipelineProps) {
  return (
    <Card className="ops-pipeline-card">
      <div className="ops-panel-header">
        <h2>LIVE RING LIFECYCLE STAGE PIPELINE</h2>
        <span className="ops-panel-subtitle">Real-time counts across production stages</span>
      </div>

      <div className="ops-pipeline-track">
        {stages.map((stage, idx) => (
          <div key={stage.id} className="ops-pipeline-step">
            <div className="ops-pipeline-box">
              <div className="ops-pipeline-box__header">
                <span className="ops-pipeline-box__name">{stage.name}</span>
                <Badge tone={stage.tone}>{stage.count}</Badge>
              </div>
              <div className="ops-pipeline-box__status">{stage.status}</div>
              <div className="ops-pipeline-box__desc">{stage.description}</div>
            </div>
            {idx < stages.length - 1 && <div className="ops-pipeline-arrow">➔</div>}
          </div>
        ))}
      </div>
    </Card>
  );
}
