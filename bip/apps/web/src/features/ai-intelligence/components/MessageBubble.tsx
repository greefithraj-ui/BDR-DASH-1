import type { AiMessage } from "../ai.types";
import { CitationCard } from "./CitationCard";
import { ToolActivityPanel } from "./ToolActivityPanel";

type MessageBubbleProps = {
  message: AiMessage;
};

function formatContent(content: string): string[] {
  return content.split("\n").filter((line) => line.length > 0);
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={isUser ? "ai__message ai__message--user" : "ai__message ai__message--assistant"}>
      <div className={isUser ? "ai__bubble ai__bubble--user" : "ai__bubble ai__bubble--assistant"}>
        {!isUser ? <p className="ai__bubble-author">AI Assistant · {message.timestamp}</p> : null}
        {formatContent(message.content).map((line) => (
          <p key={line} className="ai__bubble-text">
            {line}
          </p>
        ))}
      </div>

      {message.toolActivity && message.toolActivity.length > 0 ? (
        <ToolActivityPanel activities={message.toolActivity} />
      ) : null}

      {message.citations && message.citations.length > 0 ? (
        <div className="ai__citations">
          <p className="ai__citations-title">Citations</p>
          <div className="ai__citation-grid">
            {message.citations.map((citation) => (
              <CitationCard key={citation.id} citation={citation} />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
