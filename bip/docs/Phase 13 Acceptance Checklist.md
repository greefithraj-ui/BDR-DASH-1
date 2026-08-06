# Phase 13 Acceptance Checklist

## Settings Center — Layout Requirements

- [x] Route `/settings` renders the Settings Center page (via the existing `getRouteElement` pattern in `router.tsx`).
- [x] No `routes.ts` change required — `/settings` was already registered.
- [x] Page title, eyebrow label, and mock-data badges displayed.
- [x] Top KPI row (5 `MetricCard`s): Theme, Refresh Interval, Notifications Enabled, Feature Flags Enabled, Profile Status.
- [x] Two-column content: section list (left) + detail editor (right).
- [x] Reset-all bar at the bottom.

## Mock Data

- [x] Theme: Dark (default), options Light / Dark / System.
- [x] Accent Color: navy (default) + cyan, green, amber, violet swatches.
- [x] Density: Comfortable (default) / Compact.
- [x] Animations toggle (default on).
- [x] Notifications: 6 deterministic preferences with channel (Email/Push/In-app) and toggle state.
- [x] Language: English (default) + Deutsch, Français, Español, 日本語.
- [x] Time Zone: Central European Time (default) + UTC, Eastern Time, Pacific Time.
- [x] Date Format: YYYY-MM-DD (default) + 3 alternates with live examples.
- [x] Refresh Interval: 30s (default) + Off/15s/1m/5m/15m.
- [x] Auto Refresh toggle (default on), Result Cache toggle (default on).
- [x] Feature Flags: 6 flags across 4 groups, 4 on / 2 off by default.
- [x] User Preferences: Name, Role, Email (text); Default Dashboard, Time Format (selects); Weekly Digest (toggle).

## Sections

- [x] Appearance: Theme & Accent Color + Density & Motion.
- [x] Notifications: Alert Preferences with channel badges and toggles.
- [x] Localization: Language & Date Format + Time Zone.
- [x] Data Refresh: interval select + auto-refresh/cache toggles.
- [x] Feature Flags: preview capabilities with group badges.
- [x] User Preferences: profile defaults with shape-appropriate controls.

## Local Editing (No Persistence)

- [x] Every control edits local React state via `useState` only.
- [x] No API calls, no backend, no SQL, no persistence of any kind.
- [x] Real theme is never modified — theme/accent changes are preview-only mocks.
- [x] Section-level Default/Modified badges update live as edits are made.
- [x] "Reset section" restores a single section to defaults.
- [x] "Reset all" restores every section to defaults.
- [x] Page refresh restores defaults (no storage/URL persistence).

## Section List

- [x] Each section shows label, description, live one-line summary, and status badge.
- [x] Selected section is highlighted.
- [x] Clicking a section opens its editor in the detail panel.
- [x] "Back to settings" returns to the section list view.

## Dashboard KPIs

- [x] Theme (value = current theme, helper = accent color).
- [x] Refresh Interval (value = interval, helper = auto-refresh state).
- [x] Notifications Enabled (x / 6 with disabled count helper).
- [x] Feature Flags Enabled (x / 6 with preview-flag count helper).
- [x] Profile Status (Complete, "100% verified").

## Chart Policy

- [x] No business charts anywhere in the feature (no chart surfaces introduced).

## Design / Responsive

- [x] Tokens only — no hardcoded colors in `settings.css` (violet swatch uses `color-mix` of tokens).
- [x] Desktop: 5-col KPI row, 2-col content grid, 3-col radio grids.
- [x] Tablet (≤1180px): 2-col KPI row; content collapses to single column.
- [x] Mobile (≤720px): fully single-column, stacked headers, full-width controls.

## Quality Gates

- [x] `npm run lint:web` (`tsc --noEmit`) — passed.
- [x] `npm run build:web` — passed.
- [x] No modification to Foundation, Theme, Providers, Layout, Sidebar, Header, Design System, Charts, or any previously shipped feature (Executive Dashboard, Battery Dashboard, Battery Explorer, Machine Explorer, Timeline, Analytics Hub, Product Analytics, Quality Analytics, Performance Analytics, Reports, AI Intelligence Center, Administration Center).
- [x] Route mapping follows the standard `getRouteElement` pattern; `routes.ts` untouched.
- [x] No secrets, no backend calls, no API dependencies introduced.
