import type { AnalyticsCard as AnalyticsCardData } from "../analyticsHub.types";
import { AnalyticsCard } from "./AnalyticsCard";

type AnalyticsCardGridProps = {
  cards: AnalyticsCardData[];
  onPrimaryAction: (card: AnalyticsCardData) => void;
  onSecondaryAction: (card: AnalyticsCardData) => void;
};

export function AnalyticsCardGrid({ cards, onPrimaryAction, onSecondaryAction }: AnalyticsCardGridProps) {
  return (
    <section className="analytics-hub__category-grid" aria-label="Analytics categories">
      {cards.map((card) => (
        <AnalyticsCard key={card.id} card={card} onPrimaryAction={onPrimaryAction} onSecondaryAction={onSecondaryAction} />
      ))}
    </section>
  );
}
