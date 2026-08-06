import { Card } from "../../components/design-system";
import { ChartContainer } from "../../components/charts/ChartContainer";
import { AiHeader } from "./components/AiHeader";
import { ChatSidebar } from "./components/ChatSidebar";
import { ChatWindow } from "./components/ChatWindow";
import { ContextPanel } from "./components/ContextPanel";
import { ConversationHistory } from "./components/ConversationHistory";
import { PromptSuggestions } from "./components/PromptSuggestions";
import { useAiChat } from "./useAiChat";
import "./ai.css";

export function AiPage() {
  const ai = useAiChat();

  const pickFromEmptyState = (prompt: string) => {
    const target = ai.allConversations.find((item) => item.title === prompt);
    if (target) {
      ai.selectConversation(target.id);
    }
  };

  return (
    <section className="ai" aria-labelledby="ai-title">
      <AiHeader conversationCount={ai.allConversations.length} onToggleSidebar={() => ai.setSidebarOpen(!ai.sidebarOpen)} />

      <div className="ai__layout">
        <ChatSidebar open={ai.sidebarOpen} onClose={() => ai.setSidebarOpen(false)}>
          <ContextPanel
            activeOption={ai.activeContextOption}
            conversations={ai.conversations}
            onScopeChange={ai.setScope}
            options={ai.contextOptions}
          />
          <ConversationHistory conversations={ai.conversations} selectedId={ai.selectedId} onSelect={ai.selectConversation} />
        </ChatSidebar>

        <main className="ai__chat-area">
          {ai.selectedConversation ? (
            <ChatWindow
              conversation={ai.selectedConversation}
              messages={ai.messages}
              isTyping={ai.isTyping}
              input={ai.input}
              onInputChange={ai.setInput}
              onSend={ai.sendMessage}
            />
          ) : (
            <div className="ai__empty">
              <Card className="ai__empty-hero">
                <p className="ai__kicker">Start a conversation</p>
                <h2>Ask the AI Intelligence Center</h2>
                <p className="ai__subtitle">
                  Select a conversation from the sidebar, or pick a prompt below to open one. Assistant answers include mock tool activity and citation cards.
                </p>
                <PromptSuggestions label="Example conversations" prompts={ai.promptSuggestions} onPick={pickFromEmptyState} />
              </Card>
              <div className="ai__empty-charts">
                <ChartContainer title="Insight Distribution" description="Placeholder chart container for AI insight distribution across scopes." />
                <ChartContainer title="Conversation Activity" description="Placeholder chart container for conversation activity over time." />
              </div>
            </div>
          )}
        </main>
      </div>
    </section>
  );
}
