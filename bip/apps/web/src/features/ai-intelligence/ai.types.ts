export type AiMessageRole = "user" | "assistant";

export type AiToolStatus = "Running" | "Success" | "Failed";

export type AiScope = "Fleet" | "Battery" | "Machine" | "Quality" | "Production" | "Ring Lifecycle";

export type AiScopeFilter = AiScope | "All";

export type AiStatusTone = "neutral" | "success" | "warning" | "danger" | "info";

export type AiCitation = {
  id: string;
  label: string;
  source: string;
  detail: string;
};

export type AiToolActivity = {
  id: string;
  tool: string;
  description: string;
  status: AiToolStatus;
  startedAt: string;
  endedAt: string;
};

export type AiMessage = {
  id: string;
  role: AiMessageRole;
  content: string;
  timestamp: string;
  citations?: AiCitation[];
  toolActivity?: AiToolActivity[];
};

export type AiConversation = {
  id: string;
  title: string;
  scope: AiScope;
  description: string;
  createdDate: string;
  updatedDate: string;
  suggestedPrompts: string[];
  messages: AiMessage[];
};

export type AiContextOption = {
  value: AiScopeFilter;
  label: string;
  description: string;
};
