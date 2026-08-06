import { Badge } from "../../../components/design-system";

type AiHeaderProps = {
  conversationCount: number;
  onToggleSidebar: () => void;
};

export function AiHeader({ conversationCount, onToggleSidebar }: AiHeaderProps) {
  return (
    <header className="ai__hero">
      <div>
        <p className="ai__eyebrow">AI Intelligence Center</p>
        <h1 id="ai-title">AI Intelligence Center</h1>
        <p className="ai__subtitle">
          Ask questions over the platform's mock data, review structured conversations, and follow mock tool activity and citations — no LLM, no API, no backend.
        </p>
      </div>
      <div className="ai__hero-actions">
        <button className="ai__menu-button" type="button" onClick={onToggleSidebar} aria-label="Toggle conversation list">
          Conversations
        </button>
        <Badge tone="info">Mock Data</Badge>
        <Badge tone="neutral">{conversationCount} conversations</Badge>
      </div>
    </header>
  );
}
