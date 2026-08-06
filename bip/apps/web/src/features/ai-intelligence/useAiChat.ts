import { useEffect, useMemo, useRef, useState } from "react";
import { createMockReply, formatNow, getContextOptions, getMockConversations } from "./ai.mock";
import type { AiContextOption, AiMessage, AiScopeFilter } from "./ai.types";

export const aiEmptyPromptSuggestions: string[] = [
  "Executive Summary",
  "Battery Health",
  "Machine Status",
  "Quality Summary",
  "Performance Review",
  "Failure Investigation",
  "Ring Lifecycle",
  "Trend Analysis",
  "Production Summary",
  "General Questions"
];

export function useAiChat() {
  const conversations = useMemo(() => getMockConversations(), []);
  const contextOptions = useMemo(() => getContextOptions(), []);

  const [scope, setScope] = useState<AiScopeFilter>("All");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [liveMessages, setLiveMessages] = useState<AiMessage[]>([]);
  const timeoutRef = useRef<number | null>(null);

  const filteredConversations = useMemo(
    () => (scope === "All" ? conversations : conversations.filter((item) => item.scope === scope)),
    [conversations, scope]
  );

  const selectedConversation = useMemo(
    () => conversations.find((item) => item.id === selectedId) ?? null,
    [conversations, selectedId]
  );

  useEffect(() => {
    setLiveMessages(selectedConversation ? [...selectedConversation.messages] : []);
  }, [selectedConversation]);

  useEffect(
    () => () => {
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current);
      }
    },
    []
  );

  const selectConversation = (id: string) => {
    setSelectedId(id);
    setSidebarOpen(false);
  };

  const sendMessage = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || !selectedConversation || isTyping) {
      return;
    }

    const userMessage: AiMessage = {
      id: `live-user-${Date.now()}`,
      role: "user",
      content: trimmed,
      timestamp: formatNow()
    };

    setLiveMessages((current) => [...current, userMessage]);
    setInput("");
    setIsTyping(true);

    timeoutRef.current = window.setTimeout(() => {
      setLiveMessages((current) => [...current, createMockReply(selectedConversation.scope, trimmed)]);
      setIsTyping(false);
    }, 1400);
  };

  const activeContextOption: AiContextOption =
    contextOptions.find((option) => option.value === scope) ?? contextOptions[0];

  return {
    conversations: filteredConversations,
    allConversations: conversations,
    contextOptions,
    scope,
    setScope,
    activeContextOption,
    selectedConversation,
    selectedId,
    selectConversation,
    messages: liveMessages,
    input,
    setInput,
    sendMessage,
    isTyping,
    sidebarOpen,
    setSidebarOpen,
    promptSuggestions: aiEmptyPromptSuggestions
  };
}
