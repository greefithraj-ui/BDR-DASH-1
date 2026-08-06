# Battery Intelligence Platform — Master Design Document v2.0

**Phase:** 2
**Status:** PLANNING ONLY — awaiting approval before any implementation
**Scope:** A completely separate Battery Intelligence Platform (BIP). The existing BDR Dashboard is NOT modified except for one navigation button.
**Version:** 2.0 (enterprise restructure — supersedes v1.0)

---

## 1. Executive Summary

The Battery Intelligence Platform (BIP) is an **enterprise-grade, AI-driven platform** that operationalizes the data produced by the Battery Intelligence Collector (BIC). It elevates the original analytics-dashboard concept into a platform with two command surfaces:

- **Executive Dashboard** — the landing page. Answers **"What happened today?"** in under 30 seconds for management.
- **Battery Intelligence Dashboard** — the main operational page. Provides **AI-driven operational intelligence** for engineers and analysts (rankings, risk, hotspots, recommendations).

The platform organization is re-architected around business domains: **Analytics** (Operations, Production, Quality, Reliability, Performance, Trends, Comparison), a universal **Explorer** (Battery, Machine, Timeline), a complete **AI section** (Chat, Insights, Recommendations, Reports, Predictions), a template-based **Reports** module, an expanded **Administration** console, and a **universal Command Center (CTRL+K)** as the primary navigation experience.

### What does NOT change
| Item | Status |
|---|---|
| Architecture chain | BDR Dashboard → Battery Intelligence button → BIP (independent React app) → BIP API (independent FastAPI) → **read-only** BIC database — **unchanged** |
| Existing dashboard | Byte-identical except one button — **unchanged** |
| Backend / API / DB access | Read-only, same design — **unchanged** |
| React stack, FastAPI, themes, authentication | As designed — **unchanged** |
| Independent deployment | Separate origin, port, bundle, state — **unchanged** |

Only the **platform organization** is improved.

### Non-negotiable constraints
| Constraint | Rule |
|---|---|
| Existing dashboard | Must remain byte-identical except the one `window.open` button. |
| Database access | BIP API connects with a **read-only role**; no writes to BIC or live tables. |
| Independence | No shared UI state, no shared bundle, no runtime coupling with the dashboard. |
| AI | All LLM calls go through the dedicated AI gateway; tools are read-only and every answer is cited. |
| Future-readiness | Authentication architected now, enabled later without UI rework. |

---

## 2. Entry Point (the one dashboard change)

- Location: BDR Dashboard header (top-right).
- Behavior: `<button onClick={() => window.open('http://localhost:3100', '_blank', 'noopener')}>🧠 Battery Intelligence</button>`
- Pure navigation: no bundling, importing, or shared state. Separate origin isolates storage, JS, and lifecycle.

```
Current Dashboard (:3001)
        │
        │  🧠 Battery Intelligence (window.open → new tab)
        ▼
Battery Intelligence Platform (:3100)  ──►  BIP API (:8100)  ──►  BIC database (read-only)
```

---

## 3. Overall Architecture (unchanged)

### 3.1 Topology

```
┌────────────────────────────┐         ┌──────────────────────────────────────────┐
│  BDR Dashboard (unchanged) │         │  Battery Intelligence Platform :3100      │
│  React 18 + Vite :3001     │         │  React 18 + TS + Vite (independent)       │
│  └─ [🧠 Battery Intelligence]──────►│  ├─ Command Center (CTRL+K)                │
└────────────────────────────┘         │  ├─ Executive Dashboard (landing)         │
                                       │  ├─ Intelligence Dashboard (operational)  │
┌────────────────────────────┐         │  ├─ Analytics · Explorer · AI · Reports   │
│  BIC Collector (Sprint 1-2)│         │  ├─ Zustand (client) · TanStack (server)  │
│  (unchanged, continues)    │         │  └─ ECharts (charts)                      │
└───────────┬────────────────┘         └───────────────┬──────────────────────────┘
            │ writes                                    │ /api (REST, read-only)
            ▼                                           ▼
   ┌──────────────────────┐                 ┌──────────────────────────────┐
   │  PostgreSQL           │◄───────────────│  BIP API :8100 (FastAPI)     │
   │  bic + live_* tables  │  read-only SQL │  ├─ metrics/rings/events     │
   └──────────────────────┘                 │  ├─ intelligence/rankings    │
                                            │  ├─ unified search           │
                                            │  ├─ reports & export         │
                                            │  └─ AI gateway (tools, RO)   │
                                            └──────────────────────────────┘
```

### 3.2 Components and responsibilities
| Component | Responsibility |
|---|---|
| **BIP SPA** (`:3100`) | All UI: layout, routing, navigation (sidebar + Command Center), state, charts, Executive/Intelligence dashboards, Analytics, Explorer, AI section, Reports, Administration. Zero DB access. |
| **BIP API** (`:8100`) | The only component touching the BIC database. Read-only queries, aggregation, time-series, rankings/risk scoring, unified search, report/export payloads. |
| **AI Gateway** (BIP API module) | Provider-agnostic LLM client. Tool surface: `query_data`, `get_battery`, `get_timeline`, `get_metrics`, `get_rankings`, `get_recommendations`, `get_report`. Powers AI Chat, Insights, Recommendations, Reports, and Command-Center suggestions. Never writes. |
| **BIC Collector** | Unchanged. Passive data source. |

### 3.3 Why a dedicated API layer
- Security: browser never holds credentials; a least-privilege role enforces read-only.
- Separation: dashboard APIs untouched; BIP owns its data contract.
- Aggregation: heavy analytics run server-side (rankings, risk, shifts, survival).
- Future auth: tokens checked at the API boundary.

### 3.4 Key architectural decisions (unchanged, confirmed)
| Decision | Choice | Rationale |
|---|---|---|
| UI framework | React 18 + TypeScript | Independent choice; team familiarity, large ecosystem. |
| Build tool | Vite 6 | Fast dev/build; independent of dashboard tooling. |
| Client routing | React Router | SPA routing, layout routes, guards, deep links. |
| Server state | TanStack Query | Caching, refetch, dedupe, future mutation-ready. |
| Client state | Zustand | Theme, global context, UI flags, chat threads. |
| Charts | Apache ECharts | Rich analytics with theming. |
| Styling | Tailwind CSS v4 + CSS-variable tokens | Consistent dark/light theming, responsive. |
| Component base | shadcn/ui-style primitives on Radix | Accessible, composable, enterprise look. |
| API | FastAPI (Python) | Same language as BIC; typed contracts; reuses `bic` query helpers. |
| DB role | `bip_reader` (read-only) | Provable no-write guarantee at the DB level. |

---

## 4. Proposed Platform Structure (new, separate)

```
bip/                          ← new top-level directory (fully independent)
├── apps/
│   ├── web/                  ← SPA (:3100)
│   │   ├── src/
│   │   │   ├── app/          # providers, root layout, routes
│   │   │   ├── layouts/      # app shell (header, sidebar, outlet)
│   │   │   ├── pages/        # one folder per route (see Page Hierarchy)
│   │   │   ├── features/
│   │   │   │   ├── executive/      # Executive Dashboard
│   │   │   │   ├── intelligence/   # Intelligence Dashboard
│   │   │   │   ├── analytics/      # operations/production/quality/reliability/
│   │   │   │   │                    #  performance/trends/comparison
│   │   │   │   ├── explorer/       # battery / machine / timeline
│   │   │   │   ├── ai/             # chat/insights/recommendations/reports/predictions
│   │   │   │   ├── reports/        # daily/weekly/monthly/custom
│   │   │   │   ├── admin/          # administration tabs + settings
│   │   │   │   └── command/        # command center (CTRL+K)
│   │   │   ├── components/   # ui/ (primitives), charts/, data/ (tables)
│   │   │   ├── state/        # zustand stores + query hooks
│   │   │   ├── api/          # typed API client (react-query hooks)
│   │   │   ├── theme/        # tokens, dark/light, echarts themes
│   │   │   ├── i18n/         # (future) catalogs
│   │   │   ├── auth/         # AuthProvider abstraction (none-strategy now)
│   │   │   └── lib/          # formatting, time, ranking helpers
│   │   └── vite.config.ts    # dev proxy /api → :8100
│   └── api/                  ← BIP API (:8100)
│       ├── bip_api/          # FastAPI app
│       │   ├── routes/       # /metrics /intelligence /search /rings /events
│       │   │                 # /machines /products /shifts /failures /trends
│       │   │                 # /reports /export /system /ai
│       │   ├── services/     # queries over bic schema (read-only)
│       │   ├── intelligence/ # rankings, risk, hotspots, recommendations
│       │   ├── ai/           # gateway + whitelisted read-only tools
│       │   └── db.py         # read-only pool, bip_reader role
└── docs/                     # this design doc + API contract
```

---

## 5. Backend API Surface (read-only)

All endpoints `GET` except `POST /ai/*` and `POST /reports/preview` (read-only internally). Full JSON contract defined at implementation in `docs/api-contract.md`.

| Resource | Endpoint (prefix `/api`) | Purpose |
|---|---|---|
| Executive | `GET /metrics/executive` | KPI bundle for the Executive Dashboard (pass/fail, rings, machines, collector health). |
| Intelligence | `GET /intelligence/summary` | AI summary inputs: rankings, risk, hotspots, recommendations. |
| Rankings | `GET /intelligence/rankings` | Machine / product health rankings + most stable/failing/reliable. |
| Risk | `GET /intelligence/risk` | Machine risk scores, firmware risk, active issues. |
| Search | `GET /search?q=&category=` | Unified Command-Center search across all entity types. |
| Batteries | `GET /batteries` `GET /batteries/{id}` | Battery Explorer list + battery detail (lifecycle + events). |
| Events | `GET /events` `GET /events/aggregate` | Timeline stream + time-bucketed counts. |
| Machines | `GET /machines` `GET /machines/{name}` | Machine Explorer list + detail analytics. |
| Products | `GET /products` | Product × firmware rollups. |
| Shifts | `GET /shifts/{shift}` | Shift-scoped metrics. |
| Failures | `GET /failures` | Confirmed failure records + aggregates. |
| Trends | `GET /trends/{metric}` | Long-range series with buckets. |
| Comparison | `GET /comparison` | Side-by-side machine/product/firmware metrics. |
| AI | `POST /ai/chat` `POST /ai/insights` `POST /ai/recommendations` `POST /ai/reports` | Streaming AI surfaces with tool-calling over the read-only queries. |
| Reports | `GET /reports` `GET /reports/{id}` `GET /reports/templates` `POST /reports/preview` | Library + templates (daily/weekly/monthly/custom). |
| Export | `GET /export/{format}` | Export Center payloads (CSV/JSON/XLSX/PDF). |
| System | `GET /system/health` `GET /system/collector` `GET /system/ledger` | Collector/DB health; machine_checkpoint; migration ledger. |

Server-side rules: time-window bounds, `LIMIT` caps, whitelisted columns, parameterized SQL, no DDL, no writes.

---

## 6. Frontend Routing Structure

| Path | Page | Shell section |
|---|---|---|
| `/` | **Executive Dashboard** (landing) | Overview |
| `/intelligence` | **Battery Intelligence Dashboard** | Overview |
| `/analytics` | Analytics Hub | Analytics |
| `/analytics/operations` | Operations | Analytics |
| `/analytics/production` | Production | Analytics |
| `/analytics/quality` | Quality | Analytics |
| `/analytics/reliability` | Reliability | Analytics |
| `/analytics/performance` | Performance | Analytics |
| `/analytics/trends` | Trends | Analytics |
| `/analytics/comparison` | Comparison | Analytics |
| `/explorer/batteries` | Battery Explorer | Explorer |
| `/explorer/batteries/:id` | Battery Detail | Explorer |
| `/explorer/machines` | Machine Explorer | Explorer |
| `/explorer/machines/:name` | Machine Detail | Explorer |
| `/explorer/timeline` | Timeline | Explorer |
| `/ai/chat` | AI Chat | AI |
| `/ai/insights` | AI Insights | AI |
| `/ai/recommendations` | AI Recommendations | AI |
| `/ai/reports` | AI Reports | AI |
| `/ai/predictions` | AI Predictions (future) | AI |
| `/reports` | Reports Hub | Reports |
| `/reports/daily` `/reports/weekly` `/reports/monthly` `/reports/custom` | Report templates | Reports |
| `/reports/:reportId` | Report Detail | Reports |
| `/admin` | Administration (tabbed) | System |
| `/settings` | Settings | System |
| `/auth/login` (future) | Login | — |
| `*` | 404 | — |

Route guards (future): `RequireAuth` wrapper + permission checks (viewer/analyst/admin). Today the `none` strategy permits all.

---

## 7. Sidebar Navigation (redesigned)

### 7.1 Target structure (approved)

```
Overview
├── Executive Dashboard
└── Battery Intelligence Dashboard

Analytics
├── Operations
├── Production
├── Quality
├── Reliability
├── Performance
├── Trends
└── Comparison                    ← completes the group (analytics restructure)

Explorer
├── Battery Explorer
├── Machine Explorer
└── Timeline

AI
├── AI Chat
├── AI Insights
├── AI Recommendations
├── AI Reports
└── AI Predictions               ← marked "Planned"

Reports
├── Daily
├── Weekly
├── Monthly
└── Custom

System
├── Administration
└── Settings
```

> Note: `Comparison` is added under Analytics (per the Analytics restructure) to keep the group complete; `Timeline` lives under Explorer per the approved target but serves Analytics time-series needs and is cross-linked from Trends/Comparison.

### 7.2 Behavior
- Collapsible to icon-rail (≥ 1 200 px) and off-canvas drawer (mobile).
- Active item: accent bar + tinted background; section headers uppercase micro-labels.
- Badges: Battery Intelligence Dashboard (issues count), AI Chat (unread), Reports (scheduled), Administration (health alerts).
- Group headers are clickable hubs (Analytics → `/analytics`, AI → `/ai/chat`, Reports → `/reports`).
- Global context strip (machine + time range) pinned at the nav footer.

---

## 8. Command Center (universal — CTRL+K)

The **primary navigation experience**. One shortcut searches *everything*.

### 8.1 Architecture
- **Trigger:** `CTRL+K` / `⌘K` (also a header search box and `/` keyboard shortcut).
- **Two sources, one merged index:**
  - **Local index** (in-browser, built once from route config + nav tree + recent items + bookmarks) — instant.
  - **Server index** (`GET /api/search?q=…&category=…`) — batteries (serial/mac), machines, products, firmware, events, reports, settings keys.
- **Persistence:** recent queries + usage frequency in Zustand (localStorage); ranking model adapts per user.
- **Action model:** every result is an action (navigate, filter a page, prefill AI prompt, run export).

### 8.2 Search flow
1. Open palette (CTRL+K). 2. Type query (debounced ~150 ms). 3. Fire local index match + server search in parallel. 4. Merge + rank. 5. Keyboard-first navigation (arrows, Enter, Tab for actions). 6. Esc closes; selected item launches its action.

### 8.3 Ranking
`score = matchQuality(exact > prefix > fuzzy) × entityPriority × recency × userFrequency`
- Exact serial / ring MAC / machine name ranks top.
- Then routes/pages (recently used first), then batteries, machines, firmware, events, reports, AI prompts, settings.
- Result rows show category chip, title, subtitle, and primary action.

### 8.4 Categories
`Pages · Batteries · Machines · Products · Firmware · Events · Timeline · Reports · Analytics · AI actions · Settings`

### 8.5 Future AI integration
Natural-language commands ("show aqc-03 last week"), semantic/embedding search over event payloads, and "ask the AI" fallback when no exact match — routed to AI Chat with the query as a prompt.

---

## 9. Header (global chrome)

| Element | Behavior |
|---|---|
| Brand | BIP logo + name (independent of BDR). |
| Breadcrumbs | From route config (e.g., Analytics › Reliability). |
| Command trigger | Search box / CTRL+K affordance (opens Command Center). |
| Global context | Machine selector + time-range selector (platform-wide, persisted). |
| Notifications | Health alerts, collector status, report-ready. |
| Theme toggle | Light / Dark / Auto. |
| User menu | Profile, Settings, Sign out (stub). |

---

## 10. Page Design Specifications

Each spec: **Purpose · Main widgets · Charts · Tables · Filters · KPIs · Navigation · Future AI integration.**

### 10.1 Executive Dashboard (landing — `/`)
- **Purpose:** Give management a complete answer to *"What happened today?"* in under 30 seconds. Zero jargon; everything is decision-oriented.
- **Main widgets:** KPI card strip with day-over-day deltas; Today's Alerts feed; AI Executive Summary card (streamed narrative); Today's Intelligence (key lifecycle events); Weekly Comparison cards; Monthly Trend panels; Collector Health badge.
- **Charts:** Pass/Fail donut + gauge; monthly trend lines (rings, failures); weekly comparison bars with delta arrows; mini sparklines on every KPI card.
- **Tables:** Top 5 alerts; today's finalized/pending rings (compact, linked to Battery Detail).
- **Filters:** Time range (default **Today**), machine (default All), product.
- **KPIs:** Today's Performance (Pass % · Fail % · Total Rings · Active Rings · Machines Online · Pending Removals · Collector Health), Today's Alerts count, Weekly Comparison deltas, Monthly Trend direction.
- **Navigation:** Landing page; sidebar → Overview → Executive Dashboard; deep links to Intelligence, Explorer, Reports.
- **Future AI integration:** Daily auto-generated executive digest; alerts summarized by AI; trend explanations ("why did fail % rise?").

### 10.2 Battery Intelligence Dashboard (operational — `/intelligence`)
- **Purpose:** The main operational page — AI-driven intelligence for engineers/analysts. Turns raw state into ranked, prioritized, actionable output.
- **Main widgets:** Machine Health Ranking; Product Health Ranking; Failure Hotspots panel; Active Issues feed; spotlight cards (Most Stable Machine, Most Failing Machine, Most Reliable Product); Today's Recommendations (prioritized list); AI Generated Summary; AI Suggested Actions (one-click buttons that prefill AI Chat).
- **Charts:** Risk scatter (machine risk vs event volume); firmware risk bar; hotspot heatmap (machine × slot × time); trend sparklines on rankings.
- **Tables:** Machine ranking table (score, risk, active issues, trend); product ranking table; firmware risk table.
- **Filters:** Time range, machine, product, risk threshold slider.
- **KPIs:** Machine Risk Score (0–100), Firmware Risk, Active Issues, recommendation count, ranking deltas vs yesterday.
- **Navigation:** Sidebar → Overview → Battery Intelligence Dashboard; deep links to Analytics pages, Machine/Battery Detail, AI Chat.
- **Future AI integration:** Continuous anomaly scoring; risk-score explainability via AI; auto-recommendation execution with confirmation.

### 10.3 Analytics Hub (`/analytics`)
- **Purpose:** Entry point and summary for all seven analytics domains.
- **Main widgets:** Domain cards (Operations, Production, Quality, Reliability, Performance, Trends, Comparison) each with a one-line business question, sparkline, and delta.
- **Charts:** Shared event-mix bar; rings-by-state donut.
- **Tables:** Top 10 machines by event volume; top 5 products by failure rate.
- **Filters:** Global time range + machine.
- **KPIs:** Cross-domain highlights (machines online, pass %, MTBF, fill rate).
- **Navigation:** Sidebar → Analytics; each card drills into its page.
- **Future AI integration:** "Explain this week" threads the hub KPIs into AI Chat.

### 10.4 Operations (`/analytics/operations`)
- **Purpose:** *"Is the fleet running as expected today?"* — live operational health of machines, slots, and ingestion.
- **Main widgets:** Operational status cards; machine grid (online/stale/offline); slot-occupancy overview; ingestion freshness strip.
- **Charts:** Active rings over time; machine online/offline timeline; event throughput (events/min).
- **Tables:** Machine ops table (online, last seen, active rings, pending removals, source freshness).
- **Filters:** Time range, machine, status, slot.
- **KPIs:** Machines online/total, active rings, stale sources, events/min, pending removals.
- **Navigation:** Analytics → Operations; row → Machine Detail.
- **Future AI integration:** Ops anomaly alerts ("machine aqc-03 stopped reporting"); expected-vs-actual ingestion.

### 10.5 Production (`/analytics/production`)
- **Purpose:** *"How many batteries are we tracking, producing, and filling?"* — throughput and mix.
- **Main widgets:** Production counters (new rings today, slot fill rate, product mix); capacity card.
- **Charts:** New rings per day (bar); slot fill % over time (line); product mix (donut).
- **Tables:** Production summary by machine and by product.
- **Filters:** Time range, machine, product, slot.
- **KPIs:** New rings today, total tracked, slot fill rate, product distribution.
- **Navigation:** Analytics → Production.
- **Future AI integration:** Production forecast; fill-rate drop explanations.

### 10.6 Quality (`/analytics/quality`)
- **Purpose:** *"What is our quality and data integrity?"* — pass/fail, firmware quality, cross-source mismatches.
- **Main widgets:** Pass/Fail gauge; quality score card; data-mismatch counter (BDR_ONLY/RINGS_ONLY); firmware quality list.
- **Charts:** Pass % trend; quality score by product × firmware; mismatch counts over time.
- **Tables:** Quality matrix (product × firmware × pass/fail/mismatch); recent mismatch events.
- **Filters:** Time range, product, firmware, machine.
- **KPIs:** Pass %, Fail %, mismatch count, firmware pass rate, quality score.
- **Navigation:** Analytics → Quality.
- **Future AI integration:** Defect correlation ("failures correlate with firmware 1.1 on product PRO").

### 10.7 Reliability (`/analytics/reliability`)
- **Purpose:** *"How long do batteries live and how often do they fail?"* — reliability engineering view.
- **Main widgets:** MTBF card; failure-rate card; survival-curve card; lifecycle-duration card.
- **Charts:** Kaplan–Meier survival curves (by product/firmware); time-to-failure histogram; failure-rate trend.
- **Tables:** Confirmed failures with lifecycle duration (from `ring_history` + `ring_events`); each links to Battery Detail.
- **Filters:** Time range, product, firmware, machine, end reason.
- **KPIs:** MTBF, failure rate per active ring, median lifecycle, survival @90d.
- **Navigation:** Analytics → Reliability.
- **Future AI integration:** Remaining-useful-life estimates; failure-mode clustering.

### 10.8 Performance (`/analytics/performance`)
- **Purpose:** *"Who is performing best/worst?"* — benchmarking machines and products against each other.
- **Main widgets:** Benchmark leaderboard; performance score cards; outlier flag list.
- **Charts:** Metric distributions (box plots); machine radar (health, availability, failure); percentile bands.
- **Tables:** Machine benchmark table (score, percentile, trend); product benchmark table.
- **Filters:** Metric selector, time range, machine, product.
- **KPIs:** Performance score, percentile rank, delta vs prior period.
- **Navigation:** Analytics → Performance.
- **Future AI integration:** Performance-regression alerts; root-cause suggestions for outliers.

### 10.9 Timeline (Explorer — `/explorer/timeline`)
- **Purpose:** Chronological event stream across all rings/machines — the platform's historian (serves Explorer and Analytics needs).
- **Main widgets:** Timeline control (granularity, play/pause, live toggle); event-type legend; density histogram.
- **Charts:** Event counts over time (area/bar, stacked by type).
- **Tables:** Virtualized event stream (time, machine, slot, battery, type, reason) with infinite scroll; row → Battery Detail; type filter chips.
- **Filters:** Date range, machine, battery, event type, source.
- **KPIs:** Events in range, events today, type breakdown.
- **Navigation:** Sidebar → Explorer → Timeline; cross-linked from Trends/Comparison.
- **Future AI integration:** Period summarization; anomaly events flagged.

### 10.10 Trends (`/analytics/trends`)
- **Purpose:** Long-horizon patterns and changes on any metric.
- **Main widgets:** Metric picker; aggregation-window picker; smoothing/outlier toggles.
- **Charts:** Multi-series time series with smoothing overlay; change-point markers; trend-slope annotation.
- **Tables:** Metric summary per window bucket.
- **Filters:** Metric, window (1h/6h/1d/7d), machine, product, date range.
- **KPIs:** Current vs prior delta, trend direction, outlier count.
- **Navigation:** Analytics → Trends.
- **Future AI integration:** Forecast overlay; narrative "why did this metric shift?".

### 10.11 Comparison (`/analytics/comparison`)
- **Purpose:** Side-by-side comparison of machines, products, or firmware on chosen metrics.
- **Main widgets:** Entity picker (A vs B, or multi-select); metric selector; delta cards.
- **Charts:** Overlaid series; grouped bars; delta bar (A vs B).
- **Tables:** Side-by-side metric table with highlight of the winner per metric.
- **Filters:** Entity set, metric set, time range.
- **KPIs:** Delta %, winner per metric.
- **Navigation:** Analytics → Comparison.
- **Future AI integration:** Auto-comparison narrative; "why is A better than B?".

### 10.12 Battery Explorer (universal search — `/explorer/batteries`)
- **Purpose:** The **Google Search of the platform** — one search box to find any battery by any attribute.
- **Main widgets:** Large unified search bar; facet chips; saved searches; result count.
- **Charts:** State distribution donut of the result set.
- **Tables:** Battery result table (serial, ring MAC, product, firmware, machine, slot, state, first/last seen, end reason) with sort/pagination; row → Battery Detail.
- **Filters:** Serial Number, Ring MAC, Product, Firmware, Machine, Slot, Shift, Timeline (seen-in-range), Failure History (has finalized/failure), Event History, Lifecycle state, End Reason.
- **KPIs:** Result totals by state.
- **Navigation:** Sidebar → Explorer → Battery Explorer; deep-linked from everywhere.
- **Future AI integration:** Semantic search ("the battery we replaced on aqc-02 in June"); similar-battery suggestions.

### 10.13 Battery Detail (`/explorer/batteries/:id`)
- **Purpose:** Complete lifecycle truth for one battery.
- **Main widgets:** Identity card (serial, MAC, name, product, firmware); lifecycle timeline (OBSERVED → TRACKING → PENDING_REMOVAL → FINALIZED from `state_history`); decision summary card (`ring_history.decision_summary`); current/next machine+slot; failure-history block.
- **Charts:** Presence bar (present/absent over time); slot history on the machine.
- **Tables:** Full `ring_events` history; related batteries (same machine/slot over time).
- **Filters:** Event type, date range.
- **KPIs:** Time-in-state, confirmations, final end reason.
- **Navigation:** Any battery reference deep-links here.
- **Future AI integration:** "Summarize this battery's life" narrative.

### 10.14 Machine Explorer + Detail (`/explorer/machines` · `/explorer/machines/:name`)
- **Purpose:** Find and inspect any machine and its full battery history.
- **Main widgets:** Machine search/filter grid; machine detail: health card, slot map, battery history, checkpoint data (`machine_checkpoint`), risk score.
- **Charts:** Machine ring counts over time; slot-occupancy heatmap; event frequency.
- **Tables:** Batteries on this machine (state, slot, serial, last seen) → Battery Detail; recent events; historical batteries finalized on this machine.
- **Filters:** Machine name, state, slot, firmware, time range, online status.
- **KPIs:** Health score, active rings, pending removals, failures, last-seen freshness, machine risk.
- **Navigation:** Explorer → Machine Explorer; linked from dashboards and rankings.
- **Future AI integration:** Per-machine anomaly summary; "what changed on this machine?".

### 10.15 AI Chat (`/ai/chat`)
- **Purpose:** Natural-language conversation over all platform data; the central AI surface.
- **Main widgets:** Streaming chat thread; suggested prompts; tool-activity indicator; context pill (selected machine/battery/time); "ask about this" actions from other pages prefill threads.
- **Charts/tables:** AI answers render inline as cards, charts, or tables via a safe renderer; every data claim carries a source citation.
- **Tables:** Conversation history (browser-persisted now, server later).
- **Filters:** Context scope (global / machine / battery / time), data-only mode toggle.
- **KPIs:** Response latency, tool success, citation count.
- **Navigation:** Sidebar → AI → AI Chat; contextual "Ask AI" actions everywhere.
- **Future AI integration:** Agentic multi-turn tool use; memory of past conversations; scheduled digests.

### 10.16 AI Insights (`/ai/insights`)
- **Purpose:** Autonomous, always-on pattern discovery — insights surfaced without being asked.
- **Main widgets:** Insight feed (ranked by significance); insight detail panel; dismiss/acknowledge actions; source data citation.
- **Charts:** Supporting mini-charts per insight.
- **Tables:** Insight list (title, category, confidence, impact, related entity, time window).
- **Filters:** Category, confidence threshold, entity, date range.
- **KPIs:** Insights today, actionable insights, confidence distribution.
- **Navigation:** AI → AI Insights; insights deep-link to the relevant Analytics page.
- **Future AI integration:** Scheduled insight generation; learning from acknowledged/ignored insights.

### 10.17 AI Recommendations (`/ai/recommendations`)
- **Purpose:** Prioritized, actionable recommendations the operator can act on.
- **Main widgets:** Recommendation queue (priority-sorted); status pipeline (new → accepted → done / dismissed); one-click "ask in chat" to explore rationale.
- **Charts:** Recommendation impact estimates.
- **Tables:** Recommendation list (priority, title, affected entities, expected impact, status).
- **Filters:** Status, category, machine, product.
- **KPIs:** Open recommendations, acceptance rate, implemented count.
- **Navigation:** AI → AI Recommendations; integrated with Intelligence Dashboard's "Today's Recommendations".
- **Future AI integration:** Recommendation execution workflows with confirmation; learning from outcomes.

### 10.18 AI Reports (`/ai/reports`)
- **Purpose:** Generate and schedule narrative reports written by AI over platform data.
- **Main widgets:** Report generator (scope, time range, tone, template); scheduled report list; generation status.
- **Charts:** Reports embed platform charts.
- **Tables:** Generated reports (title, type, run time, status); report content with citations.
- **Filters:** Type, status, date range, owner.
- **KPIs:** Reports generated, scheduled count, generation success rate.
- **Navigation:** AI → AI Reports; feeds the Reports module.
- **Future AI integration:** Self-authoring weekly "intelligence brief"; anomaly-focused narratives.

### 10.19 AI Predictions (future — `/ai/predictions`)
- **Purpose:** Forecast and failure-prediction module — **planned, not implemented**.
- **Main widgets:** Module status banner ("Planned — data readiness"); model registry cards (status: Planned); data-readiness gauges.
- **Charts:** Experimental forecast previews (clearly labeled); remaining-useful-life placeholder.
- **Tables:** Model catalog; training-data coverage.
- **Filters:** n/a (stub).
- **KPIs:** Data readiness %, models active, coverage days.
- **Navigation:** AI → AI Predictions (badge: Planned).
- **Future AI integration:** ML models over `ring_history`/`ring_events`; explanations via AI Chat.

### 10.20 Reports (`/reports` — Daily / Weekly / Monthly / Custom)
- **Purpose:** Structured, exportable, schedule-able reports by cadence.
- **Main widgets:** Report library grid (template, schedule, last run, status); template pages: **Daily** (yesterday's summary), **Weekly** (weekly comparison), **Monthly** (trends + executive summary), **Custom** (builder: scope, metrics, charts, schedule, recipients); preview; export.
- **Charts:** Per-template dashboard of platform charts (state mix, trends, machine summaries).
- **Tables:** Report history (run time, status, errors, duration); report output tables.
- **Filters:** Template, status, date range, owner.
- **KPIs:** Reports due, last-run status, scheduled count.
- **Navigation:** Sidebar → Reports; AI Reports feed in here.
- **Future AI integration:** Auto-generated narrative sections; anomaly-focused briefs.

### 10.21 Administration (tabbed console — `/admin`)
Nine areas as tabs:
| Tab | Purpose & content |
|---|---|
| **Machines** | Machine registry: name, status, last rings/bdr seen, checksum (`machine_checkpoint`); enable/disable for display. |
| **Collector** | BIC collector activity: last processed, ingestion health, freshness; event throughput. |
| **Database** | Schema version, migration ledger (`schema_version`), table stats, read-only connection health, drift check. |
| **AI Services** | AI provider status, model selection, tool whitelist, prompt/scope toggles, data-only mode, usage/rate info. |
| **Users** (future) | Roles (viewer/analyst/admin), user list, permission matrix — stubbed now. |
| **Audit Logs** | Platform audit trail (exports, report runs, admin actions, settings changes). |
| **Backups** | (Future) backup/snapshot status of BIC read replicas; export-of-record snapshots. |
| **Export Center** | Bulk exports: CSV/JSON/XLSX/PDF for batteries, events, reports, admin data; export history. |
| **System Health** | DB reachable, collector active, schema current, AI gateway up, data-source freshness, uptime. |

- **Main widgets:** Health cards, ingestion charts, ledger table, export queue.
- **KPIs:** Machines online/total, collector last activity, schema version, overdue sources, export success rate.
- **Navigation:** Sidebar → System → Administration.
- **Future AI integration:** Ops log summarization; anomaly reports on ingestion.

### 10.22 Settings (`/settings`)
- **Purpose:** User preferences and platform configuration.
- **Main widgets/form groups:** Appearance (theme, accent); Locale (timezone, date/number formats); Data (refresh interval, default range); Notifications (alerts, report-ready); Shifts (definitions for Shift analytics); Features (toggle Prediction stub); AI (scope, data-only mode); Command Center (recent/ranking reset).
- **KPIs:** n/a. **Charts:** n/a. **Filters:** n/a.
- **Navigation:** Sidebar → System → Settings.
- **Future AI integration:** n/a (settings govern AI surfaces).

---

## 11. UI Design System (unchanged design, now platform-wide)

### 11.1 Design tokens (CSS variables)
`--color-*`, `--surface-*`, `--text-*`, `--border-*`, `--radius-*`, `--space-*`, `--shadow-*`, `--font-*`, `--chart-*`. Two themes (light/dark) set the same token set; a `.dark` class on `<html>` swaps values instantly. No hard-coded colors.

| Token group | Examples |
|---|---|
| Brand | primary (energy cyan), primary-hover, on-primary |
| Semantic | success, warning, danger, info, neutral |
| Surface | surface-0 (canvas), surface-1 (card), surface-2 (raised), overlay |
| Text | primary, secondary, muted, inverse |
| Chart | categorical 8-color; diverging; sequential heatmap |
| Shape | radius-sm/md/lg; shadow-sm/md/lg |

### 11.2 Dark / Light themes
- Both themes fully specified now; header toggle + auto-follow-OS; persisted.
- ECharts receives the active theme so charts match cards.
- Contrast ≥ 4.5:1 body text in both themes.
- Light = cool grays + cyan; dark = deep slate canvas, elevated surfaces, brighter cyan accents.

### 11.3 Cards
Standard card: optional header (title, actions, inline KPI), body (widget/chart/table), footer (source, "updated X min ago", link). Elevation tokens: default / interactive / modal. Skeletons preserve geometry.

### 11.4 Charts (ECharts)
Wrapped in `ChartCard` (title, legend, tooltip, empty state, export PNG/SVG). Shared series conventions (state colors, dashed = finalized). All charts respect the global time range.

### 11.5 Typography & spacing
Type scale 12/14/16/20/24/32; micro-labels 11 px uppercase; 4 px grid; 24 px gutter; 16 px card padding.

### 11.6 Responsive layout
| Breakpoint | Layout |
|---|---|
| < 768 px | Sidebar → drawer; KPI grids 2-col; tables scroll horizontally; single-column charts. |
| 768 – 1 200 px | Icon-rail sidebar; KPI grids 2–3 col; 2-col grids collapse. |
| > 1 200 px | Full sidebar; KPI grids 4–6 col; analytics 12-col grid with spans. |

---

## 12. State Management (unchanged)

| Layer | Tool | Holds |
|---|---|---|
| Server state | TanStack Query | All API data; cache keys per scope; stale times 30 s–5 m. |
| Client/UI | Zustand | Theme, global context, sidebar, Command Center index/recent, notifications, chat threads. |
| URL state | React Router + `searchParams` | Filters, pagination, selection — deep-linkable. |
| Auth (future) | Zustand + `AuthProvider` | Session, user, permissions. |

Rule: filters live in URL; heavy data debounced and validated.

---

## 13. Loading / Empty / Error States (unchanged)
- **Loading:** skeleton cards matching geometry; chart skeletons.
- **Empty:** consistent empty-state (icon, title, guidance, action).
- **Error:** per-card retry; global banner for API unreachable; degraded-mode banner when DB stale but reachable.
- **Freshness:** "updated X min ago" footers; global refresh.

---

## 14. Accessibility (unchanged)
Keyboard-navigable nav/tables, ARIA on cards/actions, focus rings in both themes, reduced-motion support, data tables behind every chart.

---

## 15. Authentication — Future Ready (unchanged)
- `AuthProvider` interface with pluggable strategies; today the **`none`** strategy (single implicit user).
- Future: OIDC/SSO/local behind the same interface; roles viewer/analyst/admin; route guards + API authorization; `POST /ai/*` and admin routes carry per-role capability.
- `/auth/login` reserved now.

---

## 16. Deployment & Operations (unchanged)
- Dev: web `:3100` (Vite, `/api` proxied to `:8100`); api `:8100` (uvicorn, read-only role).
- Prod: same ports via PM2 (matching repo pattern) or container; dashboard button URL stays `http://localhost:3100`.
- Env: `bip/.env` — DB DSN (read-only), API port, AI key, feature flags. Never committed.
- Health: `/api/system/health` surfaces in header.

---

## 17. Phased Implementation Plan (updated)

| Phase | Content |
|---|---|
| 0 | BIP scaffold (web + api), read-only DB role, health endpoint, app shell, theming, routing skeleton, **Command Center** trigger. |
| 1 | **Executive Dashboard** + Battery Explorer + Battery Detail + Timeline (core read views). |
| 2 | **Battery Intelligence Dashboard** (rankings/risk/hotspots) + Analytics (Operations, Production, Quality, Reliability, Performance, Trends, Comparison). |
| 3 | **AI section** (Chat → Insights → Recommendations → Reports) + Reports module (daily/weekly/monthly/custom). |
| 4 | Administration (9 tabs) + Settings + AI Predictions stub + global-context polish. |
| 5 | Auth enablement (per-role guards) if requested. |
| 6 | The single dashboard button (`window.open`), added last after BIP is stable. |

Each phase ends with a review gate; BIP is demo-able standalone from Phase 1.

---

## 18. Out of Scope / Guardrails (unchanged)
- No changes to the existing dashboard except the one button (added last).
- No writes to any database by BIP (DB-level enforced via `bip_reader`).
- No shared runtime state, storage keys, or bundles with the dashboard.
- No re-implementation or scraping of dashboard APIs/business logic.
- AI never mutates data; tools read-only and always cited.

---

## 19. Approval Gate

This v2.0 document is the master design reference. **No code will be written until approval.** On approval, implementation starts at Phase 0.

Open questions for the reviewer:
1. Confirm ports (`:3100` web, `:8100` API) and the dashboard button URL.
2. Confirm the `bip/` directory and unchanged stack.
3. Confirm read-only DB role creation is acceptable.
4. Confirm the sidebar placement of `Comparison` (Analytics) and `Timeline` (Explorer).
5. Confirm Executive Dashboard = landing page (`/`) and Intelligence Dashboard = `/intelligence`.

---

## Appendix A — Complete Information Architecture

```
BIP PLATFORM
├── Overview
│   ├── Executive Dashboard          → Today's Performance · Pass/Fail · Total/Active Rings ·
│   │                                  Machines Online · Pending Removals · Collector Health ·
│   │                                  Today's Alerts · AI Executive Summary · Today's Intelligence ·
│   │                                  Weekly Comparison · Monthly Trend
│   └── Battery Intelligence Dashboard→ Machine/Product Health Rankings · Failure Hotspots ·
│                                        Machine/Firmware Risk · Active Issues · Most Stable/Failing ·
│                                        Most Reliable Product · Recommendations · AI Summary/Actions
├── Analytics
│   ├── Operations                    → fleet health, machines online, slots, ingestion freshness
│   ├── Production                    → new rings, slot fill, product mix
│   ├── Quality                       → pass/fail, firmware quality, mismatches
│   ├── Reliability                   → MTBF, survival, lifecycle, failure rate
│   ├── Performance                   → benchmarking, percentiles, outliers
│   ├── Trends                        → long-range patterns, change points
│   └── Comparison                    → A/B multi-metric side-by-side
├── Explorer
│   ├── Battery Explorer              → universal search (serial/mac/product/firmware/machine/
│   │                                    slot/shift/timeline/failures/events/lifecycle/end reason)
│   ├── Machine Explorer              → machines, health, slot maps, battery history
│   └── Timeline                      → chronological event stream
├── AI
│   ├── AI Chat                       → natural language over data (tools, citations)
│   ├── AI Insights                   → autonomous pattern discovery
│   ├── AI Recommendations            → prioritized actionable queue
│   ├── AI Reports                    → scheduled narrative reports
│   └── AI Predictions (future)       → forecasting / RUL placeholders
├── Reports
│   ├── Daily / Weekly / Monthly      → cadence templates
│   └── Custom                        → builder + schedule + export
├── System
│   ├── Administration                → Machines · Collector · Database · AI Services · Users(f) ·
│   │                                    Audit Logs · Backups · Export Center · System Health
│   └── Settings                      → appearance · locale · data · notifications · shifts · features
└── Command Center (CTRL+K)           → global search + navigation over ALL of the above
```

## Appendix B — Complete Sidebar Structure

```
Overview
├── Executive Dashboard
└── Battery Intelligence Dashboard

Analytics
├── Operations
├── Production
├── Quality
├── Reliability
├── Performance
├── Trends
└── Comparison

Explorer
├── Battery Explorer
├── Machine Explorer
└── Timeline

AI
├── AI Chat
├── AI Insights
├── AI Recommendations
├── AI Reports
└── AI Predictions (Planned)

Reports
├── Daily
├── Weekly
├── Monthly
└── Custom

System
├── Administration
└── Settings
```

## Appendix C — Complete Page Hierarchy

```
/                                   Executive Dashboard            (landing)
/intelligence                       Battery Intelligence Dashboard
/analytics                          Analytics Hub
/analytics/operations               Operations
/analytics/production               Production
/analytics/quality                  Quality
/analytics/reliability              Reliability
/analytics/performance              Performance
/analytics/trends                   Trends
/analytics/comparison               Comparison
/explorer/batteries                 Battery Explorer
/explorer/batteries/:id             Battery Detail
/explorer/machines                  Machine Explorer
/explorer/machines/:name            Machine Detail
/explorer/timeline                  Timeline
/ai/chat                            AI Chat
/ai/insights                        AI Insights
/ai/recommendations                 AI Recommendations
/ai/reports                         AI Reports
/ai/predictions                     AI Predictions (future)
/reports                            Reports Hub
/reports/daily                      Daily report template
/reports/weekly                     Weekly report template
/reports/monthly                    Monthly report template
/reports/custom                     Custom report builder
/reports/:reportId                  Report Detail
/admin                              Administration (9 tabs)
/settings                           Settings
/auth/login                         Login (future)
*                                   404
```

## Appendix D — User Navigation Flow

```
Launch (button) → Executive Dashboard (/)
   ├─ drill "Today's Alerts" → Timeline (filtered today)
   ├─ drill KPI → Battery Intelligence Dashboard (/intelligence)
   │     └─ ranking row → Machine Detail
   │     └─ hotspot → Battery Detail
   ├─ "Ask AI" → AI Chat (prefilled with context)
   └─ CTRL+K anytime → Command Center → any page/entity/action

Executive → /intelligence → Reports → Custom builder → Export
Engineer  → Battery Explorer (search) → Battery Detail → Timeline → Reliability
Analyst   → Analytics Hub → Trends → Comparison → AI Insights → AI Recommendations
Admin     → /admin → System Health → Collector → Export Center
```

## Appendix E — Executive User Journey

1. Opens BIP from the dashboard button → lands on **Executive Dashboard**.
2. Reads the AI Executive Summary + Today's Alerts; scans KPI strip (Pass %, Fail %, Machines Online, Pending Removals, Collector Health).
3. Notices fail % up vs yesterday → checks Weekly Comparison and Monthly Trend.
4. Clicks a pending-removal count → Battery Intelligence Dashboard for context.
5. Uses CTRL+K → "weekly report" → Reports → Weekly → Generate → Export.
6. Never touches raw data; every answer is summarized, cited, and drillable.

**Goal satisfied:** a complete picture in under 30 seconds, with safe drill-down.

## Appendix F — Engineer User Journey

1. Opens BIP → CTRL+K → searches a serial number → Battery Detail.
2. Reviews lifecycle timeline and `state_history`/`decision_summary`; sees the ring was PENDING_REMOVAL and finalized with end reason.
3. Opens Machine Detail for the machine/slot; checks slot history and machine risk.
4. Jumps to **Battery Intelligence Dashboard** → Machine Health Ranking → sees the failing machine ranked; expands risk factors.
5. Opens AI Recommendations → accepts an actionable recommendation; explores rationale via AI Chat with source citations.
6. Verifies on the Timeline and, for systemic patterns, Reliability/Performance analytics.

**Goal satisfied:** find → understand → act, with ranked intelligence at each step.

## Appendix G — AI User Journey

1. User asks in AI Chat: "Which batteries were finalized in the last 30 days and why?"
2. Gateway resolves to `get_battery`/`query_data` tools (read-only, cited); response renders a table + state donut with citations.
3. From the same thread, user clicks "Run as insight" → AI Insights persists the pattern; user can schedule it.
4. AI Insights later flags a firmware-risk correlation → AI Recommendations proposes an action (e.g., firmware review on product PRO).
5. User generates an **AI Report** (Weekly intelligence brief) embedding the findings and schedules it.
6. Everything is cited, read-only, and reproducible.

## Appendix H — Future Expansion Roadmap

| Horizon | Items |
|---|---|
| Near (Phase 5–6) | Auth enablement; dashboard button; global-context polish; report scheduling delivery. |
| Next | AI Predictions (forecasting/RUL); notifications (push/email); insight learning loop; semantic search embeddings. |
| Medium | Multi-site/multi-fleet support; data export marketplace; custom widgets; i18n. |
| Long | Predictive maintenance playbooks; automated remediation workflows (with confirmation); machine-learning model registry; on-prem/cloud deployment variants; external integrations via API (read-only consumer). |

---

**Version 2.0 — waiting for review before implementation.**
