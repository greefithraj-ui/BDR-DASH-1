import React from "react";
import { ExceptionItem } from "../useOperationsCenter";
import "./OperationalQueue.css";

interface OperationalQueueProps {
  exceptions: ExceptionItem[];
  selectedRingId: string | null;
  onSelectRing: (ringId: string) => void;
}

export function OperationalQueue({ exceptions, selectedRingId, onSelectRing }: OperationalQueueProps) {
  return (
    <div className="opsc-queue">
      <div className="opsc-queue-header">
        <h3 className="opsc-queue-title">Operational Queue</h3>
        <span className="opsc-queue-count">{exceptions.length} ITEMS</span>
      </div>
      <div className="opsc-queue-list">
        {exceptions.map((ex) => {
          const isSelected = selectedRingId === ex.ringId;
          const isCritical = ex.severity === "critical";

          return (
            <div 
              key={ex.id} 
              className={`opsc-queue-item ${isSelected ? 'selected' : ''} ${isCritical ? 'critical' : ''}`}
              onClick={() => onSelectRing(ex.ringId)}
            >
              <div className="opsc-queue-item-left">
                <div className="opsc-queue-item-ring">{ex.ringId}</div>
                <div className="opsc-queue-item-machine">{ex.machineId}</div>
              </div>
              <div className="opsc-queue-item-center">
                <div className="opsc-queue-item-type">{ex.type}</div>
                <div className="opsc-queue-item-reason">{ex.reason}</div>
              </div>
              <div className="opsc-queue-item-right">
                <div className={`opsc-queue-severity-badge ${ex.severity}`}>
                  {ex.severity.toUpperCase()}
                </div>
              </div>
            </div>
          );
        })}
        {exceptions.length === 0 && (
          <div className="opsc-queue-empty">
            ✓ No items requiring immediate attention.
          </div>
        )}
      </div>
    </div>
  );
}
