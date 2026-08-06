import { Badge, Card } from "../../../components/design-system";
import type { AccentColor, ThemeName } from "../settings.types";

export const THEME_OPTIONS: { value: ThemeName; label: string; description: string }[] = [
  { value: "bip-dark", label: "Dark", description: "Default dark theme" },
  { value: "bip-light", label: "Light", description: "Light theme" },
  { value: "system", label: "System", description: "Follow system preference" }
];

export const ACCENT_OPTIONS: { value: AccentColor; label: string }[] = [
  { value: "navy", label: "Navy" },
  { value: "cyan", label: "Cyan" },
  { value: "green", label: "Green" },
  { value: "amber", label: "Amber" },
  { value: "violet", label: "Violet" }
];

type ThemeSettingsPanelProps = {
  theme: ThemeName;
  accentColor: AccentColor;
  onChange: (patch: Partial<{ theme: ThemeName; accentColor: AccentColor }>) => void;
};

export function ThemeSettingsPanel({ theme, accentColor, onChange }: ThemeSettingsPanelProps) {
  return (
    <Card>
      <div className="settings__section-header">
        <div>
          <p className="settings__kicker">Appearance</p>
          <h3>Theme & Accent Color</h3>
        </div>
        <Badge tone="info">Preview only</Badge>
      </div>

      <p className="settings__field-label">Theme</p>
      <div className="settings__radio-grid">
        {THEME_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`settings__radio-card${theme === option.value ? " settings__radio-card--active" : ""}`}
            aria-pressed={theme === option.value}
            onClick={() => onChange({ theme: option.value })}
          >
            <span className="settings__radio-card-label">{option.label}</span>
            <span className="settings__radio-card-desc">{option.description}</span>
          </button>
        ))}
      </div>

      <p className="settings__field-label">Accent Color</p>
      <div className="settings__swatch-row">
        {ACCENT_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`settings__swatch settings__swatch--${option.value}${
              accentColor === option.value ? " settings__swatch--active" : ""
            }`}
            aria-label={option.label}
            aria-pressed={accentColor === option.value}
            title={option.label}
            onClick={() => onChange({ accentColor: option.value })}
          >
            <span className="settings__swatch-inner" />
          </button>
        ))}
      </div>
      <p className="settings__field-hint">
        Selected accent: <strong>{accentColor}</strong> (mock preview — the live theme is not modified)
      </p>
    </Card>
  );
}
