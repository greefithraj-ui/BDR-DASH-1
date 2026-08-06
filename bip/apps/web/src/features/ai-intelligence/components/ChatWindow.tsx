import { Badge, Card } from "../../../components/design-system";
import type { AiConversation, AiMessage } from "../ai.types";
import { MessageList } from "./MessageList";
import { PromptSuggestions } from "./PromptSuggestions";

type ChatWindowProps = {
  conversation: AiConversation;
  input: string;
  isTyping: boolean;
  messages: AiMessage[];
  onInputChange: (value: string) => void;
  onSend: (text: string) => void;
};

export function ChatWindow({ conversation, input, isTyping, messages, onInputChange, onSend }: ChatWindowProps) {
  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSend(input);
  };

  return (
    <Card className="ai__chat-window">
      <header className="ai__chat-header">
        <div>
          <p className="ai__kicker">Conversation</p>
          <h2>{conversation.title}</h2>
          <p className="ai__chat-context">{conversation.description}</p>
        </div>
        <div className="ai__chat-badges">
          <Badge tone="info">{conversation.scope}</Badge>
          <Badge tone="neutral">updated {conversation.updatedDate}</Badge>
        </div>
      </header>

      <MessageList messages={messages} isTyping={isTyping} />

      <PromptSuggestions prompts={conversation.suggestedPrompts} onPick={onSend} />

      <form className="ai__composer" onSubmit={handleSubmit}>
        <input
          className="ai__control ai__composer-input"
          type="text"
          value={input}
          placeholder={`Ask about ${conversation.scope} context…`}
          aria-label="Message"
          onChange={(event) => onInputChange(event.target.value)}
        />
        <button className="ai__button" type="submit" disabled={isTyping || input.trim().length === 0}>
          Send
        </button>
      </form>
    </Card>
  );
}
