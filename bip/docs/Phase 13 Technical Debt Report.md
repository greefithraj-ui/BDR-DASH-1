# Phase 13 Technical Debt Report

## Items Introduced in Phase 13

### 1. Settings Are Not Persisted
- All edits live in a single `useState` and are lost on refresh by design (mission requirement: local React state only, no persistence).
- **Impact**: The Settings Center is a static mock; a real settings feature would need persistence, server sync, and per-user storage.
- **Deferred**: Wire persistence (localStorage or an API) behind the hook boundary when real settings are introduced. The `useSettings` surface is already shaped for this swap.

### 2. Per-Section "Changed" Detection Uses JSON Diff
- `changedGroups` compares `JSON.stringify(current[key])` against `JSON.stringify(defaults[key])`.
- **Impact**: Field-order-sensitive and O(n) per render for the six sections; fine at this scale but would not scale to a large settings object.
- **Deferred**: Use a deep-equality utility or track a dirty-field set on each update.

### 3. Theme/Accent Mock Is Not Wired to the Real Theme
- Theme and accent swatches are preview-only strings; the platform theme tokens are never touched (required behavior).
- **Impact**: The preview does not visually demonstrate the selected theme/accent on the live UI, so users cannot see the effect.
- **Deferred**: When real theme support is enabled, map `ThemeName`/`AccentColor` onto the theme system and apply tokens.

### 4. Time Zone / Language Are Static Selects
- The time-zone and language options are hardcoded arrays inside components (`TimeZonePanel`, `LanguagePanel`) rather than derived from the mock module or a shared locale config.
- **Impact**: Duplicated config that must be kept in sync with any future i18n/time-zone work.
- **Deferred**: Move locale option arrays into `settings.mock.ts` or a shared localization config.

### 5. Duplicate Toggle / Radio / Select Markup
- The toggle switch (`settings__toggle`), radio-card, and select-field patterns are repeated across six panels.
- **Impact**: Repetitive JSX; a design-system `Toggle`, `RadioCard`, and `Select` would DRY this up.
- **Deferred**: Promote reusable form controls into the design system.

### 6. No Unit Tests
- `settings.mock.ts` defaults, the `changedGroups` diff, and the hook's update helpers are not covered by tests (the repo has no test runner configured).
- **Impact**: Structural changes to the settings contract or diff logic could go uncaught.
- **Deferred**: Add contract tests once a test framework (Vitest) is introduced.

## Pre-Existing Debt Carried Forward (unchanged)

- **Large single JS chunk** (~1,147 kB, ~355 kB gzip) — ECharts bundled into one chunk; `vite build` emits a >500 kB warning. Introduced in Phase 2.5.
  - Suggested fix: route-level lazy loading (`React.lazy`) or `manualChunks` splitting ECharts.
- No test framework configured for the web app.
- No URL/state persistence for UI state (including the settings selection state).
- `routes.ts` requires an additive registry entry for top-level paths not already present (first seen in Phase 11; `/settings` already existed).

## Recommendations

- Persist settings via the `useSettings` hook boundary (localStorage or API) when real settings arrive.
- Replace JSON-diff dirty detection with a dirty-field set or deep-equality utility.
- Wire theme/accent previews to the real theme system when it supports runtime theming.
- Centralize locale/time-zone options in the mock module or a shared config.
- Promote `Toggle`/`RadioCard`/`Select` form controls into the design system.
- Introduce Vitest for contract tests on mock providers and hooks.
- Consider `React.lazy` for settings/admin/dashboard/analytics routes to reduce the initial bundle.
