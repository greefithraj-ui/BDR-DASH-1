# Phase 11 Technical Debt Report

## Items Introduced in Phase 11

### 1. Simulated Typing Indicator Relies on a Timer
- `useAiChat.sendMessage` appends a user message, sets `isTyping`, then uses a 1.4s `setTimeout` to append the canned reply. The timer is stored in a ref and cleared on unmount, but if a user sends a message and immediately switches conversations, the scheduled reply is appended to the new conversation's list (the timer closure reads the old `selectedConversation.scope`).
- **Impact**: A stale reply can appear in the wrong conversation during rapid switching.
- **Deferred**: Clear the pending timer (or cancel via an AbortController-style guard) inside `selectConversation` when the selection changes.

### 2. Live Replies Are Canned Per Scope, Not per Prompt
- `createMockReply(scope, prompt)` ignores the prompt text and returns a fixed per-scope paragraph, so any user follow-up in a scope gets the same answer.
- **Impact**: Multi-turn conversations (e.g., Trend Analysis follow-up) are only meaningful because the mock stored a real second exchange; live sends look repetitive.
- **Deferred**: Build a small prompt→template matcher or a per-conversation reply pool once a real assistant is available.

### 3. `createMockReply` and `formatNow` Use Wall-Clock Time
- Live messages get `Date.now()`-based ids and the current wall-clock time, so live chat is not fully deterministic even though the stored conversations are.
- **Impact**: Minor; reproduced live sessions will show different timestamps.
- **Deferred**: Inject a clock or time source when determinism across sessions matters.

### 4. Live Messages Are Not Persisted to the Conversation
- Sent messages live only in `useAiChat` component state; they are not written back into `conversations` (mock is memoized and read-only), so the history list counts remain fixed and a reload loses live messages.
- **Impact**: The UI is session-only by design, but the conversation list doesn't reflect appended messages.
- **Deferred**: Move messages into an updatable store (or write back into the mock shape) when persistence is required.

### 5. No Unit Tests
- `ai.mock.ts` shape, the scope filter, and the hook's send/typing flow are not covered by tests (the repo has no test runner configured).
- **Impact**: Structural changes to the mock contract or chat state could go uncaught.
- **Deferred**: Add contract/hook tests once a test framework (Vitest) is introduced.

### 6. `routes.ts` Required a New Registry Entry
- Unlike prior phases (whose target paths already existed in `routes.ts`), `/ai` was not registered, so a single additive entry was required for the `getRouteElement` branch to fire.
- **Impact**: `routes.ts` changed for the first time across phases; small, additive, and documented, but it sets a precedent that future one-off paths need a registry entry.
- **Deferred**: Revisit whether route registration should become part of the standard wiring instructions for new top-level paths.

## Pre-Existing Debt Carried Forward (unchanged)

- **Large single JS chunk** (~1,095 kB, ~344 kB gzip) — ECharts bundled into one chunk; `vite build` emits a >500 kB warning. Introduced in Phase 2.5.
  - Suggested fix: route-level lazy loading (`React.lazy`) or `manualChunks` splitting ECharts.
- No test framework configured for the web app.
- No URL/state persistence for UI state.

## Recommendations

- Clear the pending reply timer when the selected conversation changes.
- Introduce a per-conversation reply pool (or prompt matcher) so live sends feel less canned.
- Inject a clock source to keep live chat reproducible.
- Persist live messages back into the conversation model when storage exists.
- Introduce Vitest for contract tests on mock providers and hooks.
- Consider `React.lazy` for dashboard/analytics/chat routes to reduce the initial bundle.
