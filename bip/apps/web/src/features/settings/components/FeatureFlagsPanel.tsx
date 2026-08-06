import { Badge, Card } from "../../../components/design-system";
import type { FeatureFlag } from "../settings.types";

type FeatureFlagsPanelProps = {
  flags: FeatureFlag[];
  onToggle: (id: string) => void;
};

const GROUP_TONE: Record<string, "info" | "success" | "warning" | "neutral"> = {
  Intelligence: "info",
  Reports: "success",
  Appearance: "warning",
  Analytics: "neutral"
};

export function FeatureFlagsPanel({ flags, onToggle }: FeatureFlagsPanelProps) {
  return (
    <Card>
      <div className="settings__section-header">
        <div>
          <p className="settings__kicker">Feature Flags</p>
          <h3>Preview Capabilities</h3>
        </div>
        <Badge tone={flags.filter((item) => item.enabled).length === flags.length ? "success" : "info"}>
          {flags.filter((item) => item.enabled).length} of {flags.length} enabled
        </Badge>
      </div>

      <div className="settings__preference-list">
        {flags.map((item) => (
          <div key={item.id} className="settings__preference-row">
            <div className="settings__preference-copy">
              <span className="settings__preference-label">{item.label}</span>
              <span className="settings__preference-desc">{item.description}</span>
              <Badge tone={GROUP_TONE[item.group] ?? "neutral"}>{item.group}</Badge>
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
