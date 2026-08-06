import type { AiMessage } from "../ai.types";
import { CitationCard } from "./CitationCard";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";

type MessageListProps = {
  isTyping: boolean;
  messages: AiMessage[];
};

export function MessageList({ isTyping, messages }: MessageListProps) {
  return (
    <div className="ai__messages" aria-live="polite">
      {messages.map((item) => (
        <MessageBubble key={item.id} message={item} />
      ))}
      {isTyping ? <TypingIndicator /> : null}
    </div>
  );
}
