# Phase 14 Architecture Review

## Overview

Phase 14 adds the Prediction Center as a self-contained feature under `apps/web/src/features/prediction/`. It follows the established pattern (types, mock module, hook, presentational page, token-based CSS) and introduces no changes to the platform foundation or any previously shipped features.

## Layering

```
PredictionPage (composition / route target)
  ├── usePrediction                     (single useState for selected model, memoized mock data)
  │   ├── prediction.mock.ts getMockModels / getMockKpis  (deterministic source of truth)
  │   └── filteredModels / selectedModel                 (derived view models)
  ├── PredictionToolbar                  (search + status + owner filters)
  ├── PredictionKpiRow                   (inline 5 MetricCards)
  ├── PredictionModelCards              (model name, description, status, View Details)
  ├── PredictionReadinessPanel          (placeholder section)
  ├── PredictionDatasetPanel            (placeholder section)
  ├── PredictionScenarioPanel          (placeholder section)
  ├── PredictionHistoryPanel            (placeholder section)
  ├── (inline) Model Detail View        (Back, summary grid, 5 ChartContainer placeholders)
    └── PredictionDetailPanel           (detail shell, back button, summary grid)
 prediction.types.ts   (shared types)
 prediction.mock.ts    (deterministic mock models + KPIs)
 prediction.css        (feature-scoped, token-based styles)
```

## Data Flow

1. `usePrediction` initializes one `useState<string | null>` for selected model; models and KPIs are memoized from `getMockModels()` and `getMockKpis()`.
2. Filters (search, status, owner) drive a `useMemo` computed `filteredModels`; owners are hardcoded in the mock.
3. Detail view is local UI state: `setSelectedModelId` sets the selected model; the page renders the detail panel alongside the same mock data, no API or persistence.

## Component Principles

- **Container/presentational split**: only `PredictionPage` + `usePrediction` hold state; every subcomponent is props-driven.
- **Single responsibility**: 9 components, each rendering one region. Reuse across list and detail is minimal (no deep composability yet).
- **Stable keys**: model IDs (m1–m6), KPIs (kpi-models, etc.).
- **No business charts**: all charts are `ChartContainer` placeholders.

## State Management

- Two `useState`s: selected model ID and filter object. No global store, context, or router state.
- Filtering computed on every render via memoized `filteredModels`.

## Styling

- `prediction.css` uses only design tokens; dark theme inherited via token swaps.
- Class prefix `prediction__` / `prediction__hero`, etc.
- Breakpoints: ≤1180px collapses KPI row and model list to 2 columns; ≤720px goes fully single-column with stacked headers.

## Routing

- Wired through the existing `getRouteElement` switch in `router.tsx` — the same pattern used for Phases 1–13.
- `/prediction` was not present in `routes.ts`, so a single additive entry `{ path: "/prediction", label: "Prediction Center" }` was inserted (same precedent as `/ai` in Phase 11 and `/admin` in Phase 12). No other route entries modified.

## Mock Strategy

- The mock module is the single contact point for fake model data. Models are static and deterministic; replacing with an API later only changes `prediction.mock.ts`, leaving components and hooks intact.

## Dependencies Added

- None. Phase 14 consumes only existing design-system primitives (`Badge`, `Card`, `MetricCard`, `EmptyState`, `ChartContainer`).
