# Battery Intelligence Platform — Performance Baseline

Version 0.3.0. Measured 2026-08-05 against the live API on `127.0.0.1:8100` (single uvicorn worker, localhost, warm process). All values are wall-clock request latency.

## Read endpoints (average of 3 runs)

| Endpoint | avg (ms) | p95 (ms) | payload |
| --- | --- | --- | --- |
| `/api/health` | 51 | 7 | 149 B |
| `/api/v1/metrics?page_size=20` | 307 | 300 | 591 B |
| `/api/v1/machines?page_size=20` | 24 | 25 | 3 332 B |
| `/api/v1/rings?page_size=20` | 34 | 32 | 2 811 B |
| `/api/v1/timeline?page_size=20` | 13 | 10 | 114 B |
| `/api/v1/analytics/summary` | 390 | 422 | 552 B |
| `/api/v1/quality/summary` | 309 | 305 | 519 B |
| `/api/v1/performance/summary` | 304 | 303 | 523 B |
| `/api/v1/administration/overview` | 7 | 8 | 355 B |
| `/api/v1/settings` | 19 | 23 | 609 B |
| `/api/v1/system/info` | 4 | 4 | 214 B |
| `/api/v1/prediction/models` | 7 | 7 | 924 B |
| `/api/v1/reports?page=1&page_size=20` | 96 | 88 | 3 322 B |

## Report generation (single run, all 10 types)

Generation: 0.92–1.37 s per report (mean ≈ 1.1 s).

Downloads (per report type, worst-case figures across the ten types):

| Format | latency | size |
| --- | --- | --- |
| csv | 7–30 ms | 0.7–80 kB |
| xlsx | 40–368 ms | 5–44 kB |
| pdf | 15–782 ms | 2–85 kB |

## Frontend build

Vite 6.4.3, production build ≈ 10.5 s, 875 modules. Chunk split via `vite.config.ts` `manualChunks`:

| Chunk | size (raw) | size (gzip) |
| --- | --- | --- |
| `react-vendor` | 249 kB | 80 kB |
| `index` | 262 kB | 56 kB |
| `echarts` | 644 kB | 221 kB |
| CSS | 109 kB | 13 kB |

The main bundle dropped from ~1.15 MB (single file) to a ~262 kB `index` chunk; chart-heavy pages load echarts on demand.

## Conclusions

- All read endpoints respond in under ~0.4 s on localhost; nothing blocks the event loop for the pageable reads.
- Report generation (~1 s) is acceptable for an on-demand feature; PDF on the largest report (Battery Lifecycle) peaks at ~0.8 s.
- The echarts chunk is the dominant payload; acceptable for an internal analytics tool. Future work: route-level lazy loading of chart pages.
