import { Badge, Card } from "../../../components/design-system";
import type { DateFormatName, LanguageName } from "../settings.types";

const LANGUAGE_OPTIONS: LanguageName[] = ["English", "Deutsch", "Français", "Español", "日本語"];

const DATE_FORMAT_OPTIONS: { value: DateFormatName; example: string }[] = [
  { value: "YYYY-MM-DD", example: "2026-08-03" },
  { value: "DD/MM/YYYY", example: "03/08/2026" },
  { value: "MM/DD/YYYY", example: "08/03/2026" },
  { value: "DD.MM.YYYY", example: "03.08.2026" }
];

type LanguagePanelProps = {
  language: LanguageName;
  dateFormat: DateFormatName;
  onChangeLanguage: (language: LanguageName) => void;
  onChangeDateFormat: (dateFormat: DateFormatName) => void;
};

export function LanguagePanel({ language, dateFormat, onChangeLanguage, onChangeDateFormat }: LanguagePanelProps) {
  return (
    <Card>
      <div className="settings__section-header">
        <div>
          <p className="settings__kicker">Localization</p>
          <h3>Language & Date Format</h3>
        </div>
        <Badge tone="neutral">{language}</Badge>
      </div>

      <label className="settings__select-field" htmlFor="settings-language">
        <span>Language</span>
        <select
          id="settings-language"
          value={language}
          onChange={(event) => onChangeLanguage(event.target.value as LanguageName)}
        >
          {LANGUAGE_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>

      <p className="settings__field-label">Date Format</p>
      <div className="settings__radio-grid settings__radio-grid--compact">
        {DATE_FORMAT_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`settings__radio-card${dateFormat === option.value ? " settings__radio-card--active" : ""}`}
            aria-pressed={dateFormat === option.value}
            onClick={() => onChangeDateFormat(option.value)}
          >
            <span className="settings__radio-card-label">{option.value}</span>
            <span className="settings__radio-card-desc">{option.example}</span>
          </button>
        ))}
      </div>
    </Card>
  );
}
