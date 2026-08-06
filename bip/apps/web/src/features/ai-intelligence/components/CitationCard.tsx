import { Badge } from "../../../components/design-system";
import type { AiCitation } from "../ai.types";

type CitationCardProps = {
  citation: AiCitation;
};

export function CitationCard({ citation }: CitationCardProps) {
  return (
    <article className="ai__citation">
      <div className="ai__citation-head">
        <Badge tone="neutral">{citation.source}</Badge>
        <span className="ai__citation-label">{citation.label}</span>
      </div>
      <p>{citation.detail}</p>
    </article>
  );
}
