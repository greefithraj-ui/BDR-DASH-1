import React from "react";
import { RingFocus, formatTimerHHMMSS } from "../useOperationsCenter";
import "./InspectorWorkspace.css";

interface InspectorWorkspaceProps {
  focus: RingFocus | null;
}

export function InspectorWorkspace({ focus }: InspectorWorkspaceProps) {
  if (!focus) {
    return (
      <div className="opsc-inspector empty">
        <div className="opsc-inspector-empty-state">
          <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 8v4l3 3"/>
          </svg>
          <h3>No Active Selection</h3>
          <p>Select a Battery Ring from the Operational Queue to open the Inspector Workspace.</p>
        </div>
      </div>
    );
  }

  const isCritical = focus.currentStateToken === "pending-removal" || focus.currentStateToken === "failed";

  return (
    <div className="opsc-inspector">
      <div className="opsc-inspector-header">
        <div className="opsc-inspector-title">
          <h2>{focus.ringId}</h2>
          <span className="opsc-inspector-sn">{focus.serialNumber}</span>
        </div>
        <div className={`opsc-inspector-badge ${focus.currentStateToken}`}>
          {focus.stateLabel.toUpperCase()}
        </div>
      </div>

      <div className="opsc-inspector-body">
        {/* Recommended Action Panel */}
        <div className={`opsc-action-panel ${isCritical ? 'critical' : ''}`}>
          <div className="opsc-action-header">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            RECOMMENDED ACTION
          </div>
          <div className="opsc-action-content">
            {focus.requiredAction}
          </div>
          <div className="opsc-action-footer">
            <button className="opsc-btn primary">EXECUTE ACTION</button>
            <button className="opsc-btn secondary">OVERRIDE</button>
          </div>
        </div>

        {/* Context Grid */}
        <div className="opsc-context-grid">
          <div className="opsc-context-card">
            <div className="opsc-context-label">LOCATION</div>
            <div className="opsc-context-val">{focus.machineId}</div>
          </div>
          <div className="opsc-context-card">
            <div className="opsc-context-label">STATE TIMER</div>
            <div className="opsc-context-val mono">{formatTimerHHMMSS(focus.currentDurationSeconds)}</div>
          </div>
          <div className="opsc-context-card">
            <div className="opsc-context-label">OPERATOR</div>
            <div className="opsc-context-val">OP-44</div>
          </div>
          <div className="opsc-context-card">
            <div className="opsc-context-label">TELEMETRY</div>
            <div className="opsc-context-val healthy">✓ HEALTHY</div>
          </div>
        </div>
      </div>
    </div>
  );
}
