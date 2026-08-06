# BIC Test Suite

Unit and integration tests for the Battery Intelligence Collector
(Architecture Specification v1.0, Sprint Guide v1.0).

## Running

From the repository root:

```
python -m pytest tests/ -v
```

`pytest.ini` scopes collection to `tests/` via `testpaths` so the legacy
ad-hoc `test_*.py` scripts at the repository root are never collected.

## Shared fixtures (tests/conftest.py)

| Fixture | Returns | Purpose |
|---|---|---|
| `bic_config` | `BicConfig` from `load_config()` | Spec-fixed config (cadence 30 s, freshness 60 s, N=3, grace 120 s) |
| `zero_cadence_config` | `BicConfig(cadence=0)` | Fast poll-loop tests without sleeping |
| `shutdown_event` | fresh `threading.Event` | Clean-shutdown / interruptibility tests |
| `pg_available` | `bool` | True only when local PostgreSQL is reachable |
| `scratch_db` | uninitialized `BicDatabase` on `bic_scratch_<uuid>` | Snapshot-before-migration tests; never touches `bic`/`public` |
| `scratch_schema` | `BicDatabase` on a fully migrated `bic_scratch_<uuid>` | PG integration tests; schema dropped after the test |
| `reader_db` | `(db, schema_name)` with scratch live-table shapes | Reader PG tests; no BIC tables present, never touches `public.live_*` |

PG-dependent fixtures skip cleanly when psycopg2 or PostgreSQL is unavailable,
so the suite stays green in CI (which has neither).

## Test modules

| File | Scope |
|---|---|
| `test_config.py` | `bic.config` spec constants (Sprint 1, T1.1) |
| `test_main.py` | `bic.main` poll-loop framework (Sprint 1, T1.2) |
| `test_fixtures.py` | Golden fixture corpus + `fixture_loader` (Sprint 1, T1.4) |
| `test_schema.py` | `bic.schema` unit tests, no DB (Sprint 2, T1) |
| `test_db.py` | `bic.db` unit tests, no DB (Sprint 2, T1) |
| `test_pg_integration.py` | `bic.schema` + `bic.db` against a scratch schema, PG required (Sprint 2, T1) |
| `test_reader.py` | `bic.reader` pure logic (join, freshness, mismatch), no DB (Sprint 2, T2) |
| `test_reader_pg_integration.py` | `bic.reader` against scratch live-table shapes, PG required (Sprint 2, T2) |
| `test_validation.py` | `bic.validation` rules and result model, no DB (Sprint 2, T3) |
| `test_validation_pg_integration.py` | reader → engine end-to-end against scratch live tables, PG required (Sprint 2, T3) |
| `test_validation_perf.py` | Validation Engine performance/memory bounds, no DB (Sprint 2, T3) |

## CI

`.github/workflows/bic.yml` runs `python -m pytest tests/ -v` on Python 3.12
for every push/PR touching `bic/`, `tests/`, `pytest.ini`, or CI config.
CI has no PostgreSQL, so integration tests are skipped there.

## Conventions

- No test may connect to a production database or depend on environment state.
- PG tests run only against a disposable `bic_scratch_*` schema and verify the
  `bic` and `public` schemas are never modified.
- Golden fixtures are loaded via the `tests/fixtures/` corpus (Sprint 1, T1.4).
