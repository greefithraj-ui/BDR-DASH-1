import { Badge, Card } from "../../../components/design-system";
import type { SettingsGroupKey } from "../settings.types";

export type SettingsSummaryRow = {
  id: SettingsGroupKey;
  label: string;
  description: string;
  summary: string;
  changed: boolean;
};

type SettingsSummaryPanelProps = {
  rows: SettingsSummaryRow[];
  selectedGroup: SettingsGroupKey | null;
  onSelect: (key: SettingsGroupKey) => void;
};

export function SettingsSummaryPanel({ rows, selectedGroup, onSelect }: SettingsSummaryPanelProps) {
  return (
    <Card>
      <div className="settings__section-header">
        <div>
          <p className="settings__kicker">Settings</p>
          <h2>Preferences</h2>
        </div>
        <Badge tone="neutral">{rows.length} sections</Badge>
      </div>
      <div className="settings__group-list">
        {rows.map((row) => (
          <button
            key={row.id}
            type="button"
            className={`settings__group-row${selectedGroup === row.id ? " settings__group-row--selected" : ""}`}
            aria-pressed={selectedGroup === row.id}
            onClick={() => onSelect(row.id)}
          >
            <span className="settings__group-info">
              <span className="settings__group-label">{row.label}</span>
              <span className="settings__group-desc">{row.description}</span>
            </span>
            <span className="settings__group-trailing">
              <span className="settings__group-summary">{row.summary}</span>
              {row.changed ? (
                <Badge tone="warning">Modified</Badge>
              ) : (
                <Badge tone="neutral">Default</Badge>
              )}
              <span className="settings__group-chevron" aria-hidden="true">
                ›
              </span>
            </span>
          </button>
        ))}
      </div>
    </Card>
  );
}
