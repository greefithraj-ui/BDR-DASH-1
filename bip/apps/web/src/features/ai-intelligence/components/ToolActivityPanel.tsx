import { Badge } from "../../../components/design-system";
import { TOOL_STATUS_TONES } from "../ai.mock";
import type { AiToolActivity } from "../ai.types";

type ToolActivityPanelProps = {
  activities: AiToolActivity[];
};

function parseSeconds(value: string): number {
  const parts = /(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})/.exec(value);
  if (!parts) {
    return 0;
  }
  const [, y, mo, d, h, mi, s] = parts;
  return Date.UTC(Number(y), Number(mo) - 1, Number(d), Number(h), Number(mi), Number(s)) / 1000;
}

function durationLabel(startedAt: string, endedAt: string): string {
  const seconds = Math.max(0, parseSeconds(endedAt) - parseSeconds(startedAt));
  return `${seconds}s`;
}

export function ToolActivityPanel({ activities }: ToolActivityPanelProps) {
  if (activities.length === 0) {
    return null;
  }

  return (
    <div className="ai__tool-activity">
      <p className="ai__tool-activity-title">Mock tool activity</p>
      <ol className="ai__tool-timeline">
        {activities.map((activity) => (
          <li key={activity.id} className="ai__tool-step">
            <div className="ai__tool-step-head">
              <span className="ai__tool-name">{activity.tool}</span>
              <Badge tone={TOOL_STATUS_TONES[activity.status]}>{activity.status}</Badge>
            </div>
            <p className="ai__tool-desc">{activity.description}</p>
            <p className="ai__tool-time">
              {activity.startedAt} → {activity.endedAt} · {durationLabel(activity.startedAt, activity.endedAt)}
            </p>
          </li>
        ))}
      </ol>
    </div>
  );
}
