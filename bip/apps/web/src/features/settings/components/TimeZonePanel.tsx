import { Badge, Card } from "../../../components/design-system";
import type { TimeZoneName } from "../settings.types";

const TIME_ZONE_OPTIONS: TimeZoneName[] = [
  "(GMT+01:00) Central European Time",
  "(GMT+00:00) UTC",
  "(GMT-05:00) Eastern Time",
  "(GMT-08:00) Pacific Time"
];

type TimeZonePanelProps = {
  timeZone: TimeZoneName;
  onChange: (timeZone: TimeZoneName) => void;
};

export function TimeZonePanel({ timeZone, onChange }: TimeZonePanelProps) {
  return (
    <Card>
      <div className="settings__section-header">
        <div>
          <p className="settings__kicker">Localization</p>
          <h3>Time Zone</h3>
        </div>
        <Badge tone="info">{timeZone.split(") ")[0].replace("(", "")}</Badge>
      </div>
      <label className="settings__select-field" htmlFor="settings-time-zone">
        <span>Time Zone</span>
        <select
          id="settings-time-zone"
          value={timeZone}
          onChange={(event) => onChange(event.target.value as TimeZoneName)}
        >
          {TIME_ZONE_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>
      <p className="settings__field-hint">Used to display timestamps across dashboards and reports.</p>
    </Card>
  );
}
