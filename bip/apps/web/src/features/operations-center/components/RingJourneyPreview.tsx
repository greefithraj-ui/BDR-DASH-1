import { Card } from "../../../components/design-system";

export function RingJourneyPreview() {
  return (
    <Card className="opsc-card opsc-preview-card">
      <div className="opsc-panel-header">
        <h2>RING LIFECYCLE JOURNEY PREVIEW</h2>
        <span className="opsc-panel-meta">Standard Progression Flow</span>
      </div>

      <div className="opsc-journey-flow">
        <div className="opsc-journey-node">
          <div className="opsc-journey-node__box opsc-journey-node__box--assigned">
            <span className="opsc-journey-node__step">STEP 1</span>
            <span className="opsc-journey-node__title">Assigned</span>
            <span className="opsc-journey-node__desc">Station load & registration</span>
          </div>
        </div>

        <div className="opsc-journey-arrow">↓</div>

        <div className="opsc-journey-node">
          <div className="opsc-journey-node__box opsc-journey-node__box--inspection">
            <span className="opsc-journey-node__step">STEP 2</span>
            <span className="opsc-journey-node__title">Inspection</span>
            <span className="opsc-journey-node__desc">Active telemetry & testing</span>
          </div>
        </div>

        <div className="opsc-journey-arrow">↓</div>

        <div className="opsc-journey-node">
          <div className="opsc-journey-node__box opsc-journey-node__box--passed">
            <span className="opsc-journey-node__step">STEP 3</span>
            <span className="opsc-journey-node__title">Passed</span>
            <span className="opsc-journey-node__desc">Diagnostic verification clear</span>
          </div>
        </div>

        <div className="opsc-journey-arrow">↓</div>

        <div className="opsc-journey-node">
          <div className="opsc-journey-node__box opsc-journey-node__box--pending">
            <span className="opsc-journey-node__step">STEP 4</span>
            <span className="opsc-journey-node__title">Pending Removal</span>
            <span className="opsc-journey-node__desc">Queued for station unmount</span>
          </div>
        </div>
      </div>
    </Card>
  );
}
