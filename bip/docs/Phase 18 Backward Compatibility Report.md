# Phase 18 Backward Compatibility Report

## Summary

Phase 18 changes **frontend data plumbing only**. The backend contract, the frontend component tree, routing, and the public API surface are byte-identical to the end of Phase 17. No breaking changes were introduced for users, the API, or the build.

## Backend API Compatibility

- **No endpoint changes.** All 20 OpenAPI paths from Phase 17 remain, including the legacy `/api/health` alias. No routes added, removed, or re-versioned.
- **No response shape changes.** `SuccessEnvelope {data, meta}` and `PaginatedResponse {items,total,page,page_size}` unchanged; DTO field names (snake_case) unchanged.
- **No query-parameter changes.** `page`, `page_size`, `search`, `status`, `sort_by`, `sort_dir`, `date_from`, `date_to` semantics unchanged.
- **No DB/role changes.** Read-only `bip_reader`; no DML; no schema changes.
- **Independent deployments:** the API works with the Phase 17 frontend; the Phase 18 frontend works with the Phase 17 API (verified live, see Verification Report §4). The two halves are not coupled to a shared release.

## Frontend Compatibility

- **Pages, components, and routing are untouched** — every page consumes the same hook return fields it did before migration. Screenshots remain identical; only the data source changed.
- **Hook shapes preserved:** interactive hooks return the same fields (`allRecords`, `pageRecords`, `filters`, `options`, `sort`, `selected`, …); dashboard hooks return the same `{data, error, isLoading}` triple. New fields (`refresh`, `isEmpty`) are additive.
- **Design system untouched:** `EmptyState`, `LoadingSkeleton`, `Badge`, `MetricCard`, `Card`, `ChartContainer` unchanged; no new UI primitives.
- **Dependencies unchanged:** `@tanstack/react-query` was already present and wired (`QueryProvider`); no new runtime packages, no version bumps.
- **Environment variables unchanged:** `VITE_BIP_API_BASE_URL`, `VITE_BIP_API_PROXY_TARGET` semantics preserved; defaults (`/api`, `http://localhost:8100`) unchanged.

## Build & Tooling Compatibility

- `npm run lint:web` and `npm run build:web` pass from a clean tree (see Verification Report).
- No `package.json` or lockfile changes in this phase.
- The shared contracts module (`shared/contracts/health.ts`) is unchanged and still imported by `apiClient`.

## Mock Layer Compatibility

- Out-of-scope features keep their existing mock modules and behavior (`settings.mock`, `prediction.mock`, `performanceAnalytics.mock`, `ai.mock`, `administration.mock`).
- `reports.mock.ts` still exports `formatDuration`, consumed by five report components — no import paths changed.
- The eight deleted mock modules had exactly one consumer each (their feature hook), verified by grep before deletion; no dangling imports remain.

## Regression Risk Register

| Risk | Assessment | Mitigation |
|---|---|---|
| Hook shape drift breaking pages | Low — pages unmodified and type-checked (`tsc --noEmit`) | Verified build |
| API unavailable at runtime | Low — pages show existing empty/error states; no crash paths | Retry 1 + error surfaced via hooks |
| Multi-page fetch (rings/timeline/reports) | Low — `fetchAllPages` bounds by `total`; empty total returns immediately | Verified live 200s |
| Data not yet present (timeline, products, quality records) | Low — existing `EmptyState` branches render | Documented in Completion Report |
| Clock/format drift (ISO timestamps) | Low — `format.ts` guards invalid dates with `""` | Unit-level guards in one module |

## Conclusion

Phase 18 is backward compatible with Phase 17 on both sides of the HTTP boundary, introduces no dependency or tooling changes, and leaves every pre-existing component contract intact.
