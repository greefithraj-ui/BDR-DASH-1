import { Badge } from "../../../components/design-system";

type SectionHeaderProps = {
  eyebrow: string;
  title: string;
  badge?: string;
};

export function SectionHeader({ badge, eyebrow, title }: SectionHeaderProps) {
  return (
    <div className="battery-intelligence__section-header">
      <div>
        <p className="battery-intelligence__section-kicker">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      {badge ? <Badge>{badge}</Badge> : null}
    </div>
  );
}
