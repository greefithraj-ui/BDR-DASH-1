import { Badge, Card } from "../../../components/design-system";
import type { AiConversation } from "../ai.types";

type ConversationHistoryProps = {
  conversations: AiConversation[];
  onSelect: (id: string) => void;
  selectedId: string | null;
};

export function ConversationHistory({ conversations, onSelect, selectedId }: ConversationHistoryProps) {
  return (
    <Card>
      <div className="ai__panel-header">
        <div>
          <p className="ai__kicker">History</p>
          <h2>Conversations</h2>
        </div>
        <Badge tone="neutral">{conversations.length}</Badge>
      </div>
      {conversations.length === 0 ? (
        <p className="ai__empty-note">No conversations in this context scope.</p>
      ) : (
        <ul className="ai__conversation-list">
          {conversations.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className={item.id === selectedId ? "ai__conversation ai__conversation--active" : "ai__conversation"}
                onClick={() => onSelect(item.id)}
              >
                <span className="ai__conversation-title">{item.title}</span>
                <span className="ai__conversation-scope">
                  <Badge tone="info">{item.scope}</Badge>
                </span>
                <span className="ai__conversation-meta">
                  {item.messages.length} messages · updated {item.updatedDate}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
