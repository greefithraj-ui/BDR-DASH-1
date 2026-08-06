# Phase 17 Technical Debt Report

## 1. Prediction models remain in-memory

- **Where**: `app/repositories/prediction.py`, `app/services/prediction.py`.
- **Why**: the approved read-only sources contain no model catalogue; the Phase 17 mission explicitly permits keeping the placeholder.
- **Impact**: low — two endpoints (`/prediction/models[/{model_id}]`) serve static rows; contract stable.
- **Retirement**: when a prediction catalogue table exists in `bic.*`/`public.*`, replace `InMemoryListRepository` with a SQL repository (same wiring pattern as the other domains).

## 2. Ring capacity is an approximation

- **Where**: `app/services/rings.py` — `capacity_mwh = float(slot_count)`.
- **Why**: no capacity data exists in the approved sources; the response model (`Ring.capacity_mwh`) is fixed and cannot be dropped.
- **Impact**: low — value is the occupied slot count, documented in code and reports; misleading only if consumed as real MWh.
- **Retirement**: when ring master data (or `bic.ring_identities` population) provides capacity, map the real column.

## 3. Summary endpoints paginate in memory

- **Where**: metrics, analytics, quality, performance, settings, system, prediction.
- **Why**: result sets are tiny (< 20 rows); SQL pagination would add complexity for no benefit.
- **Impact**: negligible at current scale.
- **Retirement**: if these collections grow, move `LIMIT/OFFSET` into SQL like machines/rings/timeline.

## 4. No automated tests in the repo

- **Where**: whole `apps/api`.
- **Why**: pre-existing condition; the repo has no test framework configured.
- **Impact**: verification is manual (compile + smoke + server run).
- **Retirement**: add pytest + `pytest-asyncio`; at minimum cover the SQL pagination/filter/sort paths and the 404/503 handlers.

## 5. Connection-per-request model

- **Where**: `app/dependencies/database.py`.
- **Why**: consistent with the existing DI architecture.
- **Impact**: low — pooled connections are cheap; per-request acquisition is the standard pattern.
- **Retirement**: none required; if latency ever matters, a repository-side pool is a drop-in alternative.

## 6. Health endpoint couples readiness to the DB

- **Where**: `app/services/health.py` / `app/repositories/health.py`.
- **Why**: the payload reads `bic.schema_version`; `HealthResponse.status` is `Literal["ok"]`, so a DB failure surfaces as 500 rather than a degraded status.
- **Impact**: acceptable — DB availability is required for every other endpoint anyway; the legacy `/api/health` shape is preserved.
- **Retirement**: widen `status` to `ok|degraded` in a future phase if a soft-health contract is desired (would be a breaking model change).

## 7. Hardcoded business thresholds

- **Where**: `app/services/machines.py` (health score formula), `app/services/{quality,performance}.py` (80% online threshold).
- **Why**: no threshold data exists in the DB.
- **Impact**: low; documented, deterministic.
- **Retirement**: move thresholds to settings when they become configurable.

## 8. Machines in both live tables with different names

- **Where**: `app/repositories/live.py` machine union.
- **Why**: `live_rings_raw` and `live_bdr_raw` do not always share the same machine set (e.g. aqc-36 only in rings, aqc-15 only in bdr).
- **Impact**: machines are unioned; per-source freshness is tracked so partial presence is visible via `rings_at`/`bdr_at`.
- **Retirement**: none — current behavior is the correct union semantics.

## 9. `InMemoryListRepository` retained for a single domain

- **Where**: `app/repositories/base.py`.
- **Why**: only prediction uses it.
- **Impact**: small maintenance surface; `write()` raises `NotImplementedError` (501).
- **Retirement**: fold into prediction when it moves to SQL.

## 10. No index/plan tuning

- **Why**: tables are small and read-only; `jsonb_each` lateral scans are acceptable at current volume.
- **Impact**: none at current scale.
- **Retirement**: re-evaluate when live payload sizes grow (the BIC collector would be the right place to add indexes on `downloaded_at`/`machine_name`).
