# Phase 11 Architecture Review

## Overview

Phase 11 adds the AI Intelligence Center as a self-contained feature under `apps/web/src/features/ai-intelligence/`. It follows the established feature-folder pattern (types, mock provider, hook, presentational components, token-based CSS) and introduces no changes to the platform foundation. All "AI" behavior is deterministic mock content — there is no LLM, no API, and no backend.

## Layering

```
AiPage (composition / route target)
 ├── useAiChat                    (mock conversations + scope filter + chat/drill state + typing simulation)
 ├── components/AiHeader          (hero, badges, mobile sidebar toggle)
 ├── components/ChatSidebar       (in-flow sidebar on desktop; drawer + backdrop on mobile)
 │   ├── ContextPanel             (context scope selector + meta)
 │   └── ConversationHistory      (conversation list with active state)
 ├── main.ai__chat-area
 │   ├── ChatWindow               (header + MessageList + PromptSuggestions + composer)
 │   │   ├── MessageList
 │   │   │   └── MessageBubble × N
 │   │   │       ├── ToolActivityPanel   (per-message mock tool timeline)
 │   │   │       └── CitationCard × N     (per-message citation cards)
 │   │   └── TypingIndicator      (rendered by MessageList while isTyping)
 │   └── (empty state) PromptSuggestions + 2 ChartContainer placeholders
ai.types.ts   (shared types)
ai.mock.ts    (deterministic mock source + reply generator)
ai.css        (feature-scoped, token-based styles)
```

## Data Flow

1. `useAiChat` memoizes `getMockConversations()` and `getContextOptions()` once. The context-scope filter narrows the visible conversation list; the selected conversation is resolved from the full list.
2. When a conversation is selected, `liveMessages` is seeded from its mock `messages`. `sendMessage` appends a user message, sets `isTyping`, and after a 1.4s `setTimeout` appends a deterministic `createMockReply(scope)` — a per-scope canned answer with tool activity and a citation. The timeout is cleaned up on unmount.
3. Components are props-driven: the page and hook hold all state; children receive data and callbacks only.

## Component Principles

- **Container/presentational split**: only `AiPage` and `useAiChat` hold state/composition.
- **Single responsibility**: 12 components, each rendering one region. `PromptSuggestions`, `MessageList`, `ToolActivityPanel`, and `CitationCard` are reused across chat and empty-state contexts.
- **Stable keys**: conversations, messages, tool steps, and citations all keyed by id.
- **Tone system**: tool statuses map Success=success, Failed=danger, Running=info onto the design-system Badge tone contract; `TOOL_STATUS_TONES` is shared between mock and the tool panel.

## State Management

- `useState` only: scope filter, selected conversation id, input, typing flag, sidebar open, and live messages. No global store, context, or URL sync. The simulated typing uses a `setTimeout` ref cleaned up on unmount.

## Styling

- `ai.css` uses only design tokens; dark theme inherited automatically via token swaps.
- Class prefix `ai__` prevents collisions with other features.
- Responsive: desktop grid is `320px` sidebar + chat column; at ≤980px the sidebar becomes a fixed drawer (`translateX(-105%)` → open) with a token-based backdrop and a close button; at ≤720px everything stacks single-column with full-width bubbles.

## Routing

- Wired through the existing `getRouteElement` switch in `router.tsx` — the same pattern used for Phases 1–10.
- `/ai` was not present in `routes.ts` (prior phases mapped paths that already existed). Because the `getRouteElement` branch only fires for paths in the route registry, a single additive entry `{ path: "/ai", label: "AI Intelligence Center" }` was inserted in `routes.ts`. No other route entries were modified or removed.

## Mock Strategy

- The mock module is the single contact point for fake data. `buildConversations()` declaratively defines 10 conversations; a `tool()`/`cite()`/`message()`/`conversation()` set of helpers keeps each entry compact. `createMockReply` provides deterministic live replies per scope. Replacing with a real assistant later only requires changing `getMockConversations`/`createMockReply` (or the hook), leaving components intact.

## Dependencies Added

- None. Phase 11 consumes only existing design-system primitives (`Badge`, `Card`), `ChartContainer`, the shared `cn` helper, and `react` hooks.
