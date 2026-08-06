# Phase 13 Architecture Review

## Overview

Phase 13 adds the Settings Center as a self-contained feature under `apps/web/src/features/settings/`. It follows the established feature-folder pattern (types, mock module, hook, presentational components, token-based CSS), with the defining constraint that all edits live in a single local `useState` and are never persisted.

## Layering

```
SettingsPage (composition / route target)
 ├── useSettings                          (single useState<SettingsState> + selection state)
 │   ├── settings.mock.ts getDefaultSettings / getSettingGroups   (mock source of truth)
 │   └── getGroupSummary / buildKpis / changedGroups               (derived view models)
 ├── (inline) KPI row × 5 MetricCard      (Theme, Refresh Interval, Notifications, Flags, Profile)
 ├── components/SettingsSummaryPanel      (clickable section list → openGroup)
 ├── components/SettingsDetailPanel       (editor shell: header, changed badge, Back/Reset)
 │   ├── components/AppearanceSettingsPanel
 │   │   └── components/ThemeSettingsPanel
 │   ├── components/NotificationSettingsPanel
 │   ├── components/LanguagePanel  +  components/TimeZonePanel   (localization)
 │   ├── components/DataRefreshPanel
 │   ├── components/FeatureFlagsPanel
 │   └── components/UserPreferencesPanel
 └── (inline) reset-all Card
settings.types.ts    (shared types)
settings.mock.ts     (deterministic default settings)
settings.css         (feature-scoped, token-based styles)
```

## Data Flow

1. `useSettings` initializes one `useState<SettingsState>` from `getDefaultSettings()`. `defaults` is memoized so it never changes identity.
2. Every control in the feature calls one of the update helpers (`updateAppearance`, `updateLocalization`, `updateDataRefresh`, `toggleNotification`, `toggleFlag`, `updatePreference`), each performing an immutable shallow-update of the nested state. **This is the only mutation path** — no storage, no context, no URL sync.
3. View models are derived on render via `useMemo`: `kpis` (5 KPI cards), `changedGroups` (per-section JSON diff against defaults), `changedCount`, and `getGroupSummary` strings for the section list.
4. Detail selection is plain UI state: `openGroup(key)` sets `selectedGroup`; the page renders `SettingsDetailPanel` around the editor for that section, or an `EmptyState` prompt when none is selected.

## Component Principles

- **Container/presentational split**: only `SettingsPage` + `useSettings` hold state; every panel is props-driven. Panels receive plain data (`appearance`, `preferences`, `flags`, `settings`) plus narrow callbacks (`onChange(patch)`, `onToggle(id)`, `onUpdate(id, value)`).
- **Single responsibility**: 11 components, each rendering one region. `AppearanceSettingsPanel` composes `ThemeSettingsPanel` with Density & Motion; the localization editor composes `LanguagePanel` + `TimeZonePanel`.
- **Shape-driven controls**: `UserPreferencesPanel` renders a toggle, select, or text input depending on the `UserPreference` shape, so the panel stays generic.
- **Stable keys**: KPIs, sections, preferences, and flags all keyed by id.

## State Management

- `useState` only — one settings object plus one selection value. No global store, context, or persistence. All edits are ephemeral by design (mission: "local React state only").

## Styling

- `settings.css` uses only design tokens; dark theme inherited automatically via token swaps. The violet accent swatch is derived with `color-mix(in srgb, var(--color-accent) 55%, var(--color-info))` to avoid hardcoding a color.
- Class prefix `settings__` / `settings-detail__` prevents collisions with other features.
- Breakpoints: ≤1180px collapses the KPI row to 2 columns and the content grid to a single column; ≤720px goes fully single-column with stacked headers.

## Routing

- Wired through the existing `getRouteElement` switch in `router.tsx` — the same pattern used for Phases 1–12.
- `/settings` was already registered in `routes.ts` (`{ path: "/settings", label: "Settings" }`), so **no registry change was required** (unlike `/ai` in Phase 11 and `/admin` in Phase 12).

## Mock Strategy

- `settings.mock.ts` is the single contact point for default values and section metadata. Every group builder (`buildAppearance`, `buildNotifications`, …) returns plain deterministic data; `getDefaultSettings()` composes them. Components never construct settings directly, so swapping to an API later only changes the mock/hook boundary.

## Dependencies Added

- None. Phase 13 consumes only existing design-system primitives (`Badge`, `Card`, `MetricCard`, `EmptyState`) and `react` hooks. No chart components used.
