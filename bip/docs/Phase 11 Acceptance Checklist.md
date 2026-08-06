# Phase 11 Acceptance Checklist

## AI Intelligence Center — Layout Requirements

- [x] Route `/ai` renders the AI Intelligence Center page (via `getRouteElement` in `router.tsx`; `/ai` added to the route registry as the only new entry).
- [x] Page title, eyebrow label, and mock-data badge displayed.
- [x] Conversation list (sidebar) with 10 deterministic mock conversations.
- [x] Chat area with message list, prompt suggestions, and composer.
- [x] Context selector (All + 6 scopes).
- [x] Tool activity timeline per assistant message.
- [x] Citation cards per assistant message.
- [x] Typing indicator while a reply is being simulated.
- [x] Empty state shown before any conversation is selected.

## Mock Conversations

- [x] Executive Summary (Fleet)
- [x] Battery Health (Battery)
- [x] Machine Status (Machine)
- [x] Quality Summary (Quality)
- [x] Performance Review (Production)
- [x] Failure Investigation (Quality)
- [x] Ring Lifecycle (Ring Lifecycle)
- [x] Trend Analysis (Fleet)
- [x] Production Summary (Production)
- [x] General Questions (Fleet)

## Conversation Data

- [x] Each conversation has a conversation ID.
- [x] Each has a title, created date, and updated date.
- [x] Each has user messages and assistant messages (1–2 exchanges; Trend Analysis is a 2-turn follow-up).
- [x] Each has suggested prompts (clicking one sends it).
- [x] Assistant messages include mock tool activity and mock citations.
- [x] Each conversation declares a context scope.

## UI

- [x] Conversation list with scope badges, message count, updated date, active state.
- [x] Chat area renders user (accent) and assistant (card) bubbles.
- [x] Prompt suggestions rendered in both chat and empty state.
- [x] Context selector filters the conversation list by scope.
- [x] Tool activity timeline shows tool name, status badge, description, and duration.
- [x] Citation cards show source badge, label, and detail.
- [x] Typing indicator animates during the 1.4s simulated reply.
- [x] Empty state offers example prompts and 2 `ChartContainer` placeholders.

## Chat Behavior

- [x] Selecting a conversation seeds the message list from its mock messages.
- [x] Sending appends a user message, shows the typing indicator, then appends a deterministic per-scope mock reply.
- [x] Composer Send is disabled while typing or when input is empty.

## Chart Policy

- [x] No business charts — every chart surface is a `ChartContainer` placeholder (2 in the empty state).
- [x] No LLM, no API, no backend, no SQL, no PostgreSQL, no FastAPI, no tool-calling, no third-party AI provider.

## Design / Responsive

- [x] Tokens only — no hardcoded colors in `ai.css`.
- [x] Desktop: 320px sidebar + chat column; citation grid auto-fills.
- [x] Tablet (≤980px): sidebar becomes a fixed drawer with backdrop and close button.
- [x] Mobile (≤720px): single-column, stacked headers, full-width bubbles.

## Quality Gates

- [x] `npm run lint:web` (`tsc --noEmit`) — passed.
- [x] `npm run build:web` — passed.
- [x] No modification to Foundation, Theme, Providers, Layout, Sidebar, Header, Design System, Charts, or any previously shipped feature (Executive Dashboard, Battery Dashboard, Battery Explorer, Machine Explorer, Timeline, Analytics Hub, Product Analytics, Quality Analytics, Performance Analytics, Reports).
- [x] Route mapping follows the standard `getRouteElement` pattern; the only registry change is the new `/ai` entry.
- [x] No secrets, no backend calls, no API dependencies introduced.
