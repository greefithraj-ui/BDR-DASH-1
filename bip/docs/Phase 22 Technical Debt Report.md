# Phase 22 Technical Debt Report

Post-phase debt inventory. Phase 22 reduced debt substantially (dead code removed, drift corrected); the remaining items below are accepted or deferred.

## Debt cleared this phase

| Item | Impact |
| --- | --- |
| Dead backend modules (legacy report chain, broken exporter options, unported UI class) | −Maintenance surface, no more misleading imports |
| Dead frontend report/auth artifacts | −Confusing duplication with the live report feature |
| Env-file loading was silently a no-op (and briefly loaded the parent repo's `.env`) | Config now behaves as documented |
| Version drift (0.2.5 vs 0.3.0), placeholder descriptions | Trustworthy metadata |
| Health contract drift between TS and Python | Single source of truth for the contract |
| Unpinned `openpyxl`/`reportlab` | Reproducible installs |
| 1.15 MB single bundle | 78% smaller main chunk, cacheable vendor/echarts chunks |
| `check_health.py` that printed raw output | Exit-code-based validation |
| Stale `openapi-placeholder.json` | Live OpenAPI only |

## Remaining debt (accepted / deferred)

| # | Item | Severity | Notes |
| --- | --- | --- | --- |
| D1 | `bip/` not under version control | **High** | Blocker for external release; needs `git init` + baseline commit |
| D2 | No automated test suite (unit/integration); validation is script-based (`api_validation.py`, `check_health.py`) | Medium | Phase 22 used live-script validation; convert to pytest before future changes |
| D3 | Aggregate summaries recompute over the full in-memory dataset (~300–390 ms) | Low | Watch when data grows; add caching/indexing if needed |
| D4 | Charts/eChart lazy loading not done; echarts chunk still 644 kB | Low | Dynamic import per chart page |
| D5 | Root `README.md` is minimal (de-Phased but thin) | Low | Full refresh deferred to post-VCS phase |
| D6 | No API auth/rate limiting | Low-Med | Accepted risk documented in Security.md; proxy-level mitigation at deploy |
| D7 | Placeholder `BIP_DB_PASSWORD` default in code | Low | Override mandated in production; consider removing default |
| D8 | `.env.example` does not document every variable with a comment | Low | Variable names covered in Configuration.md; sync comments to the example |
| D9 | No CI pipeline (lint/build/test on push) | Medium | Add after VCS baseline; currently all checks are manual commands |
| D10 | Legacy `InMemoryListRepository` uses in-memory mock data for several endpoints | Medium | The API serves seeded data, not live DB rows, for metrics/machines/rings/timeline; wiring to live repositories is a product decision outside Phase 22 scope |

## Recommendations

1. Resolve D1 first (VCS baseline) — it unblocks D2 and D9.
2. Convert `api_validation.py` into a pytest suite (D2) as the regression safety net.
3. Add CI (D9) that runs `lint:web`, `build:web`, `py_compile`, and the pytest suite.
4. Revisit D10 as a product decision with stakeholders.
