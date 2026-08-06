import React from "react";
import "./CommandBar.css";

interface CommandBarProps {
  onRefresh: () => void;
  lastRefreshTime: string;
  isHealthy: boolean;
}

export function CommandBar({ onRefresh, lastRefreshTime, isHealthy }: CommandBarProps) {
  return (
    <header className="opsc-command-bar">
      <div className="opsc-cb-left">
        <h1 className="opsc-cb-title">Operations Command Center</h1>
        <div className={`opsc-cb-status ${isHealthy ? "healthy" : "error"}`}>
          {isHealthy ? "SYSTEM HEALTHY" : "SYSTEM DEGRADED"}
        </div>
      </div>
      
      <div className="opsc-cb-center">
        {/* Global Search / Command Palette Trigger */}
        <div className="opsc-global-search-trigger" onClick={() => {
          window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }));
        }}>
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <span>Search Rings, Machines, Actions... (Ctrl+K)</span>
        </div>
      </div>

      <div className="opsc-cb-right">
        <div className="opsc-cb-sync">
          <span>Live Sync</span>
          <span className="opsc-cb-time">{lastRefreshTime}</span>
        </div>
        <button className="opsc-cb-btn" onClick={onRefresh} title="Force Refresh">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
        </button>
      </div>
    </header>
  );
}
