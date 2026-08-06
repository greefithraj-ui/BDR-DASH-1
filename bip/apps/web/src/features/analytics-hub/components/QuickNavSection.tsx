import type { QuickNavItem } from "../analyticsHub.types";

type QuickNavSectionProps = {
  items: QuickNavItem[];
  onNavigate: (route: string) => void;
};

export function QuickNavSection({ items, onNavigate }: QuickNavSectionProps) {
  return (
    <section className="analytics-hub__quick-nav" aria-label="Quick navigation">
      <div className="analytics-hub__section-header">
        <div>
          <p className="analytics-hub__kicker">Navigation</p>
          <h2>Quick Navigation</h2>
        </div>
      </div>
      <div className="analytics-hub__quick-nav-grid">
        {items.map((item) => (
          <button key={item.id} className="analytics-hub__quick-nav-card" type="button" onClick={() => onNavigate(item.route)}>
            <h3>{item.label}</h3>
            <p>{item.description}</p>
          </button>
        ))}
      </div>
    </section>
  );
}
