import { Badge, Card } from "../../../components/design-system";
import type { AppearanceSettings } from "../settings.types";
import { ThemeSettingsPanel } from "./ThemeSettingsPanel";

const DENSITY_OPTIONS = ["Comfortable", "Compact"] as const;

type AppearanceSettingsPanelProps = {
  appearance: AppearanceSettings;
  onChange: (patch: Partial<AppearanceSettings>) => void;
};

export function AppearanceSettingsPanel({ appearance, onChange }: AppearanceSettingsPanelProps) {
  return (
    <div className="settings__stack">
      <ThemeSettingsPanel
        theme={appearance.theme}
        accentColor={appearance.accentColor}
        onChange={(patch) => onChange(patch)}
      />

      <Card>
        <div className="settings__section-header">
          <div>
            <p className="settings__kicker">Appearance</p>
            <h3>Density & Motion</h3>
          </div>
        </div>

        <p className="settings__field-label">Density</p>
        <div className="settings__radio-grid">
          {DENSITY_OPTIONS.map((option) => (
            <button
              key={option}
              type="button"
              className={`settings__radio-card${appearance.density === option ? " settings__radio-card--active" : ""}`}
              aria-pressed={appearance.density === option}
              onClick={() => onChange({ density: option })}
            >
              <span className="settings__radio-card-label">{option}</span>
              <span className="settings__radio-card-desc">
                {option === "Comfortable" ? "More spacing, fewer rows" : "Denser tables and panels"}
              </span>
            </button>
          ))}
        </div>

        <div className="settings__toggle-row">
          <div className="settings__toggle-copy">
            <span className="settings__toggle-label">Animations</span>
            <span className="settings__toggle-hint">Animate charts and panel transitions.</span>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={appearance.animations}
            aria-label="Animations"
            className={`settings__toggle${appearance.animations ? " settings__toggle--on" : ""}`}
            onClick={() => onChange({ animations: !appearance.animations })}
          >
            <span className="settings__toggle-knob" />
          </button>
        </div>
        <p className="settings__field-hint">
          <Badge tone="neutral">Mock</Badge> These options are previewed only and never applied to the live UI.
        </p>
      </Card>
    </div>
  );
}
