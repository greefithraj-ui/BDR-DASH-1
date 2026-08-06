# Phase 15 Technical Debt Report

## Items Introduced in Phase 15

### 1. Placeholder Repositories Duplicate Frontend Mock Data
- Each `repositories/*.py` embeds deterministic rows that mirror the frontend mock identities (AQC-01…AQC-08, RNG-001…, PRD-01…). The datasets are hand-maintained in two places.
- **Impact**: Drift is guaranteed once real data arrives; updates must be applied in both the API and the frontend mock modules.
- **Deferred**: A shared data contract / fixture source (or real queries) owned by one layer.

### 2. `InMemoryListRepository` Only Supports `id` Lookups
- `get_by_id` relies on `getattr(record, "id", None)` and dataset ordering; search/filter logic lives in each service.
- **Impact**: Filtering is duplicated per service and would not scale to real query-backed repositories.
- **Deferred**: Introduce a query/spec object for filtering or push filtering into repositories when real persistence lands.

### 3. Legacy `/api/health` Alias
- The health router is mounted twice (under `/api/v1` and directly under `/api`) purely for backward compatibility with `apiClient.ts` and `scripts/check_health.py`.
- **Impact**: Two URLs for one resource; the alias must be retired once consumers move to `/api/v1/health`.
- **Deferred**: Remove the alias and update the frontend client and health script in a coordinated change.

### 4. Repositories Instantiate Per-Request
- `dependencies/services.py` builds a new repository + service on every request.
- **Impact**: Trivial for in-memory placeholder data, but real repositories/sessions should be scoped correctly (per-request sessions, connection pooling).
- **Deferred**: Introduce proper session/DI scoping when database access is added.

### 5. Envelope `meta` Is Minimal
- `SuccessEnvelope.ok()` only adds `generated_at`; there is no request-id correlation, pagination metadata at the envelope level, or API version.
- **Impact**: Debugging and client-side correlation are limited.
- **Deferred**: Add request-id propagation, envelope-level pagination info, and version fields.

### 6. ErrorModel Lacks Request Context
- The standard error payload has no request id or path, making log correlation harder.
- **Impact**: Operators cannot tie an error to a specific request without the access log.
- **Deferred**: Include request-id (from middleware) in `ErrorModel`.

### 7. No Python Type-Checking or Test Tooling Configured
- The repo has no mypy/pyright config and no pytest setup; verification relied on `compileall`, import validation, and OpenAPI generation.
- **Impact**: Type errors and regressions in services/repos can go uncaught.
- **Deferred**: Add `pyproject.toml` with mypy/ruff and a pytest suite for services + OpenAPI contract.

### 8. Services Contain Filtering Logic
- The mission requires services to shape deterministic responses, but search/status filtering currently lives in each service class.
- **Impact**: Business-ish rules in the service layer; acceptable for placeholders, but real query optimization belongs in repositories.
- **Deferred**: Move filtering into repository query objects in the persistence phase.

## Pre-Existing Debt Carried Forward

- `db/session.py` remains a marker `ReadOnlyDatabaseSession` protocol; no session wiring yet (intentional for this phase).
- Frontend large single JS chunk (~1.15 MB) and no frontend test framework — out of scope for a backend phase.
- No request id / correlation tracing exists anywhere in the platform.

## Recommendations

- Adopt a single mock/fixture contract shared between the API and frontend (or replace both with the API in Phase 16/17).
- Add `pyproject.toml` with mypy + ruff and a pytest suite for services and OpenAPI contract tests.
- Add request-id middleware and include the id in `ErrorModel` and envelope `meta`.
- Remove the legacy `/api/health` alias after the frontend client and health script migrate to `/api/v1/health`.
- Plan repository scoping (per-request session, pooling) before the database phase.
