# Phase 22 Performance Review

Measured 2026-08-05 against the warm live API (`127.0.0.1:8100`, single uvicorn worker) and the production build. Full tables in `docs/Production/Performance.md`.

## Read endpoints (avg of 3)

| Endpoint | avg (ms) | p95 (ms) |
| --- | --- | --- |
| `/api/health` | 51 | 7 |
| `/api/v1/metrics?page_size=20` | 307 | 300 |
| `/api/v1/machines?page_size=20` | 24 | 25 |
| `/api/v1/rings?page_size=20` | 34 | 32 |
| `/api/v1/timeline?page_size=20` | 13 | 10 |
| `/api/v1/analytics/summary` | 390 | 422 |
| `/api/v1/quality/summary` | 309 | 305 |
| `/api/v1/performance/summary` | 304 | 303 |
| `/api/v1/administration/overview` | 7 | 8 |
| `/api/v1/settings` | 19 | 23 |
| `/api/v1/system/info` | 4 | 4 |
| `/api/v1/prediction/models` | 7 | 7 |
| `/api/v1/reports?page=1&page_size=20` | 96 | 88 |

**Assessment**: every read endpoint under ~0.4 s; pageable reads use in-memory repositories and do not block the event loop. The three aggregate summaries (~300–390 ms) recompute over the full in-memory dataset per call — acceptable now, watch when the dataset grows.

## Report generation (all 10 types)

| Type | ms | | Type | ms |
| --- | --- | --- | --- | --- |
| Executive Summary | 1195 | | Analytics Summary | 987 |
| Machine Performance | 1053 | | Timeline Report | 1006 |
| Battery Summary | 950 | | Operations Summary | 1032 |
| Battery Lifecycle | 1114 | | System Health | 941 |
| Quality Summary | 1319 | | Collector Status | 1371 |

Generation ≈ 0.9–1.4 s (mean ≈ 1.1 s) — acceptable for an on-demand report feature.

## Downloads (range across all 10 types)

| Format | latency | size |
| --- | --- | --- |
| csv | 7–30 ms | 0.7–80 kB |
| xlsx | 40–368 ms | 5–44 kB |
| pdf | 15–782 ms | 2–85 kB |

Largest PDF (Battery Lifecycle) ~0.8 s; all other formats well under 400 ms.

## Frontend build

- Vite 6.4.3, production build ≈ 10.5 s, 875 modules.
- `manualChunks` split (introduced this phase):
  - `react-vendor` 249 kB (gzip 80)
  - `index` 262 kB (gzip 56) — **was ~1.15 MB in a single file**
  - `echarts` 644 kB (gzip 221)
  - CSS 109 kB (gzip 13)

**Assessment**: main bundle cut ~78%; echarts is now isolated so chart-free pages avoid most of it. Route-level lazy loading of chart pages remains future work.

## Recommendations

1. Add an index/cache over the aggregate summaries if the in-memory dataset grows past ~10⁵ rows.
2. Keep the echarts chunk split; consider dynamic import per chart page for further initial-load reduction.
3. No regressions were observed between the pre-cleanup and post-cleanup builds.
