import React from "react";
import type { PipelineStage } from "../useOperationsCenter";
import "./LivePipeline.css";

type LivePipelineProps = {
  stages: PipelineStage[];
  onSelectRing: (ringId: string) => void;
};

export function LivePipeline({ stages }: LivePipelineProps) {
  return (
    <div className="opsc-pipeline">
      {stages.map((stage, idx) => (
        <React.Fragment key={stage.id}>
          <button className={`opsc-pipeline-stage ${stage.statusTokenKey}`}>
            <div className="opsc-pipeline-stage-count">{stage.count}</div>
            <div className="opsc-pipeline-stage-name">{stage.name}</div>
          </button>
          {idx < stages.length - 1 && (
            <div className="opsc-pipeline-arrow">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </div>
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

