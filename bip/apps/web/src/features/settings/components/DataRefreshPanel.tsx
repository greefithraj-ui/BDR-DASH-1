import { Badge, Card } from "../../../components/design-system";
import type { DataRefreshSettings, RefreshIntervalValue } from "../settings.types";

const REFRESH_OPTIONS: RefreshIntervalValue[] = ["Off", "15s", "30s", "1m", "5m", "15m"];

type DataRefreshPanelProps = {
  settings: DataRefreshSettings;
  onChange: (patch: Partial<DataRefreshSettings>) => void;
};

export function DataRefreshPanel({ settings, onChange }: DataRefreshPanelProps) {
  return (
    <Card>
      <div className="settings__section-header">
        <div>
          <p className="settings__kicker">Data Refresh</p>
          <h3>Dashboard Refreshing</h3>
        </div>
        <Badge tone={settings.refreshInterval === "Off" ? "neutral" : "success"}>
          {settings.refreshInterval === "Off" ? "Paused" : `Every ${settings.refreshInterval}`}
        </Badge>
      </div>

      <label className="settings__select-field" htmlFor="settings-refresh-interval">
        <span>Refresh Interval</span>
        <select
          id="settings-refresh-interval"
          value={settings.refreshInterval}
          onChange={(event) => onChange({ refreshInterval: event.target.value as RefreshIntervalValue })}
        >
          {REFRESH_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option === "Off" ? "Off (manual refresh)" : option}
            </option>
          ))}
        </select>
      </label>

      <div className="settings__toggle-row">
        <div className="settings__toggle-copy">
          <span className="settings__toggle-label">Auto Refresh</span>
          <span className="settings__toggle-hint">Automatically refresh dashboards on the interval.</span>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={settings.autoRefresh}
          aria-label="Auto Refresh"
          className={`settings__toggle${settings.autoRefresh ? " settings__toggle--on" : ""}`}
          onClick={() => onChange({ autoRefresh: !settings.autoRefresh })}
        >
          <span className="settings__toggle-knob" />
        </button>
      </div>

      <div className="settings__toggle-row">
        <div className="settings__toggle-copy">
          <span className="settings__toggle-label">Result Cache</span>
          <span className="settings__toggle-hint">Cache query results to reduce load.</span>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={settings.cacheEnabled}
          aria-label="Result Cache"
          className={`settings__toggle${settings.cacheEnabled ? " settings__toggle--on" : ""}`}
          onClick={() => onChange({ cacheEnabled: !settings.cacheEnabled })}
        >
          <span className="settings__toggle-knob" />
        </button>
      </div>
    </Card>
  );
}
