import { Badge, Card } from "../../../components/design-system";
import type { UserPreference } from "../settings.types";

type UserPreferencesPanelProps = {
  preferences: UserPreference[];
  onUpdate: (id: string, value: string | boolean) => void;
};

export function UserPreferencesPanel({ preferences, onUpdate }: UserPreferencesPanelProps) {
  return (
    <Card>
      <div className="settings__section-header">
        <div>
          <p className="settings__kicker">User Preferences</p>
          <h3>Profile Defaults</h3>
        </div>
        <Badge tone="success">Profile verified</Badge>
      </div>

      <div className="settings__preference-list">
        {preferences.map((item) => (
          <div key={item.id} className="settings__preference-row">
            <div className="settings__preference-copy">
              <span className="settings__preference-label">{item.label}</span>
              <span className="settings__preference-desc">{item.description}</span>
            </div>
            {typeof item.value === "boolean" ? (
              <button
                type="button"
                role="switch"
                aria-checked={item.value}
                aria-label={`Toggle ${item.label}`}
                className={`settings__toggle${item.value ? " settings__toggle--on" : ""}`}
                onClick={() => onUpdate(item.id, !item.value)}
              >
                <span className="settings__toggle-knob" />
              </button>
            ) : item.options ? (
              <label className="settings__select-field settings__select-field--inline" htmlFor={`settings-${item.id}`}>
                <span className="settings__visually-hidden">Value</span>
                <select
                  id={`settings-${item.id}`}
                  value={String(item.value)}
                  onChange={(event) => onUpdate(item.id, event.target.value)}
                >
                  {item.options.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <label className="settings__select-field settings__select-field--inline" htmlFor={`settings-${item.id}`}>
                <span className="settings__visually-hidden">Value</span>
                <input
                  id={`settings-${item.id}`}
                  type="text"
                  value={String(item.value)}
                  onChange={(event) => onUpdate(item.id, event.target.value)}
                />
              </label>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}
