# Phase 18.1 Backward Compatibility Report

## Summary

Phase 18.1 refines frontend data plumbing only. The backend contract, the component tree, routing, the design system, and the public API surface are unchanged from Phase 18. No breaking changes were introduced for users, the API, or the build.

## Backend API Compatibility

- **No backend changes at all** — no repositories, services, SQL, database, middleware, core, or models were touched (per phase constraints).
- **No endpoint changes**: all OpenAPI paths from Phase 17 remain; detail endpoints `/api/v1/rings/{id}` and `/api/v1/machines/{id}` were already present (Phase 17) and are now consumed — they were previously unused.
- **No response-shape changes**: `SuccessEnvelope`/`PaginatedResponse` and all DTO field names unchanged; `apiClient` is untouched in this phase.
- **No query-parameter changes**: `page`/`page_size` semantics unchanged.
- The Phase 18.1 frontend runs unchanged against the Phase 17 API (verified live, see Verification Report §4).

## Frontend Compatibility

- **Pages keep their layout and components** — only hero badges/subtitles, refresh buttons, and status rows were added; no grid, panel, or chart layout was altered.
- **Hook return shapes preserved**: all nine feature hooks expose the same fields the pages consumed in Phase 18 (`data`/`kpis`/`cards`/…, `filters`, `sort`, `selected`, `isLoading`, `error`, `refresh`, `isEmpty`). The two detail hooks changed shape intentionally (`{detail, isLoading, error, refresh}`) and their only consumers (the two pages) were updated in the same change — no other component consumes them.
- **Design system untouched**: no changes to `components/design-system`, theme, tokens, or CSS files. The one design-system incompatibility discovered (`Button` lacks `onClick`) was worked around with native `<button>` elements using existing classes (`ds-button`, per-feature `__button` classes).
- **Dependencies unchanged**: no new packages, no version bumps.
- **Environment variables unchanged**: `VITE_BIP_API_BASE_URL`, `VITE_BIP_API_PROXY_TARGET` semantics preserved.

## Data & Wording Compatibility

- All values continue to be sourced from the Phase 17 API; the only wording changes are presentation labels (mock → live) on the nine live features. Out-of-scope features keep their `Mock Data` badges because they remain mock-backed.
- Intentional placeholder labels (chart containers, chart descriptions, executive summary "Coming Soon") were preserved verbatim.

## Mock Layer Compatibility

- `reports.mock.ts` still exports `formatDuration`, consumed by five report components — no import paths changed.
- Out-of-scope mocks (settings, prediction, performance-analytics, ai-intelligence, administration) untouched.
- No references to the Phase 18 deleted mock providers exist (grep-verified).

## Cache Behavior Compatibility

- Query keys for shared collections keep the Phase 18 names (`["machines"]`, `["rings"]`, `["timeline","list"]`, `["reports","list"]`), so the cache identity is stable across the migration; new keys (`["metrics"]`, `["analytics-summary"]`, `["quality-summary"]`, `["performance-summary"]`, `["health"]`, detail keys) follow the same factory pattern.
- `staleTime: 30_000` consistent with Phase 18; global QueryClient options (`retry: 1`, `refetchOnWindowFocus: false`) unchanged.

## Regression Risk Register

| Risk | Assessment | Mitigation |
|---|---|---|
| Detail query key/id mismatch (MAC colons, machine names) | Low — ids come from the selected list row and are `encodeURIComponent`-escaped; verified 200 live | Verified in smoke test |
| Detail error banner always visible | Fixed — `errorMessage` is `null` when there is no error | Type-checked + code review |
| Shared cache introducing stale cross-page data | Low — 30s staleTime matches Phase 18 semantics; refresh available on every page | Refresh buttons on all pages |
| First-load skeleton replacing table layout | Low — skeleton only while `isPending && isFetching` (no data yet); refetches keep content visible | `isLoading` definition unchanged |
| `Button` design-system component | N/A — avoided entirely; native buttons with existing classes used | No design-system modification |

## Conclusion

Phase 18.1 is backward compatible with Phase 18 on both sides of the HTTP boundary, adds no dependencies, changes no API contract, and preserves every pre-existing layout and component contract.
