import { Badge, Card } from "../../../components/design-system";
import type { NotificationPreference } from "../settings.types";

type NotificationSettingsPanelProps = {
  preferences: NotificationPreference[];
  onToggle: (id: string) => void;
};

const CHANNEL_TONE: Record<NotificationPreference["channel"], "success" | "warning" | "info"> = {
  Email: "info",
  Push: "warning",
  "In-app": "success"
};

export function NotificationSettingsPanel({ preferences, onToggle }: NotificationSettingsPanelProps) {
  return (
    <Card>
      <div className="settings__section-header">
        <div>
          <p className="settings__kicker">Notifications</p>
          <h3>Alert Preferences</h3>
        </div>
        <Badge tone="neutral">{preferences.filter((item) => item.enabled).length} enabled</Badge>
      </div>

      <div className="settings__preference-list">
        {preferences.map((item) => (
          <div key={item.id} className="settings__preference-row">
            <div className="settings__preference-copy">
              <span className="settings__preference-label">{item.label}</span>
              <span className="settings__preference-desc">{item.description}</span>
              <Badge tone={CHANNEL_TONE[item.channel]}>{item.channel}</Badge>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={item.enabled}
              aria-label={`Toggle ${item.label}`}
              className={`settings__toggle${item.enabled ? " settings__toggle--on" : ""}`}
              onClick={() => onToggle(item.id)}
            >
              <span className="settings__toggle-knob" />
            </button>
          </div>
        ))}
      </div>
    </Card>
  );
}
