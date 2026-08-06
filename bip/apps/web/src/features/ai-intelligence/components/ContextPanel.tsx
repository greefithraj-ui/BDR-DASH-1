import { Badge, Card } from "../../../components/design-system";
import type { AiContextOption, AiConversation, AiScopeFilter } from "../ai.types";

type ContextPanelProps = {
  activeOption: AiContextOption;
  conversations: AiConversation[];
  onScopeChange: (scope: AiScopeFilter) => void;
  options: AiContextOption[];
};

export function ContextPanel({ activeOption, conversations, onScopeChange, options }: ContextPanelProps) {
  return (
    <Card>
      <div className="ai__panel-header">
        <div>
          <p className="ai__kicker">Context</p>
          <h2>Context Scope</h2>
        </div>
        <Badge tone="info">{activeOption.value}</Badge>
      </div>
      <label className="ai__field" htmlFor="ai-context-select">
        <span className="ai__field-label">Scope</span>
        <select
          id="ai-context-select"
          className="ai__control"
          value={activeOption.value}
          onChange={(event) => onScopeChange(event.target.value as AiScopeFilter)}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <p className="ai__context-description">{activeOption.description}</p>
      <dl className="ai__context-meta">
        <div>
          <dt>Conversations</dt>
          <dd>{conversations.length}</dd>
        </div>
        <div>
          <dt>Active Scope</dt>
          <dd>{activeOption.value}</dd>
        </div>
      </dl>
    </Card>
  );
}
