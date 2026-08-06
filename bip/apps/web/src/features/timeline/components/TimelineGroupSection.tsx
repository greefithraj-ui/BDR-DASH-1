import type { TimelineEvent, TimelineGroup } from "../timeline.types";
import { TimelineEventCard } from "./TimelineEventCard";

type TimelineGroupSectionProps = {
  group: TimelineGroup;
  onSelect: (event: TimelineEvent) => void;
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function formatDateLabel(value: string): string {
  const [year, month, day] = value.split("-");
  return `${day} ${MONTHS[Number(month) - 1]} ${year}`;
}

export function TimelineGroupSection({ group, onSelect }: TimelineGroupSectionProps) {
  const isDate = /^\d{4}-\d{2}-\d{2}$/.test(group.key);

  return (
    <section className="timeline__group" aria-label={group.label}>
      <header className="timeline__group-header">
        <h2>{isDate ? formatDateLabel(group.key) : group.label}</h2>
        <span className="timeline__group-count">
          {group.events.length} event{group.events.length === 1 ? "" : "s"}
        </span>
      </header>
      <div className="timeline__event-list">
        {group.events.map((event) => (
          <TimelineEventCard key={event.id} event={event} onSelect={onSelect} />
        ))}
      </div>
    </section>
  );
}
