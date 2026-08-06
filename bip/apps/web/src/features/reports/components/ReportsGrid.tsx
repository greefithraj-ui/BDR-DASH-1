import { Badge } from "../../../components/design-system";
import type { Report } from "../reports.types";
import { ReportCard } from "./ReportCard";

type ReportsGridProps = {
  kicker: string;
  title: string;
  badgeLabel: string;
  reports: Report[];
  onSelect: (report: Report) => void;
};

export function ReportsGrid({ kicker, title, badgeLabel, reports, onSelect }: ReportsGridProps) {
  if (reports.length === 0) {
    return null;
  }

  return (
    <section className="reports__grid" aria-label={title}>
      <div className="reports__section-header">
        <div>
          <p className="reports__kicker">{kicker}</p>
          <h2>{title}</h2>
        </div>
        <Badge tone="info">{badgeLabel}</Badge>
      </div>
      <div className="reports__card-grid">
        {reports.map((report) => (
          <ReportCard key={report.id} report={report} onSelect={onSelect} />
        ))}
      </div>
    </section>
  );
}
