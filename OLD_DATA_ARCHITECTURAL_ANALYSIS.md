# Old Data System — Complete Architectural Analysis

**Project:** BDR Dashboard  
**Date:** 2026-07-28  
**Analyst:** AI Readiness Assessment  
**Scope:** Old Data / Historical Archive subsystem  

---

## PART 1 — OLD DATA ARCHITECTURE

### Complete Data Flow

```
REMOTE AQC MACHINES (172.16.18.x — 42 machines)
  │
  │  SSH paramiko (password: 1234)
  │  SFTP from: ~/auto-dfu-tool/assembly_test_app/bdr_session.json
  │  SFTP from: ~/auto-dfu-tool/assembly_test_app/rings_config.json
  │
  ▼
┌──────────────────────────────────────────────────────┐
│  Download Layer (data/main.py)                       │
│                                                      │
│  download_all() — parallel SFTP, 16 workers          │
│  Runs: every 30s (background), or on-demand          │
│  Output: DESTINATION/bdr/{machine}.json              │
│          DESTINATION/rings/{machine}.json             │
│                                                      │
│  After each BDR download:                            │
│    archive_bdr_snapshot() → reads bdr/*.json         │
│      ↓                                               │
│      Copies to: DESTINATION/archive/{machine}/        │
│                  {YYYY-MM-DD}/{HH-MM-SS}.json        │
│      (rate-limited: once per 30 seconds)             │
│      ↓                                               │
│      Then calls:                                     │
│        1. ring_status.ingest_file_to_ring_status()   │
│           → UPSERT into ring_status table            │
│        2. HTTP POST to http://127.0.0.1:8000/        │
│           api/old-data/ingest-file                   │
│           → ingest_archive_to_pg()                    │
│           → INSERT into archive_entries table        │
│           → ALSO ring_status upsert again            │
│                                                      │
│  Separate path (30s background sync):                │
│    sync_machines_from_files()                        │
│    → UPSERT into live_bdr_raw / live_rings_raw       │
│      (overwrites per machine_name)                   │
└──────────────────────┬───────────────────────────────┘
                       │
         ┌─────────────┼──────────────┐
         ▼             ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│ JSON Archive  │ │SQLite    │ │ PostgreSQL   │
│ Files on Disk  │ │archive.db│ │ Database     │
│               │ │11.4 GB   │ │              │
│ DESTINATION/  │ │legacy,   │ │ bdr_dashboard│
│ archive/      │ │being     │ │              │
│ {machine}/    │ │migrated  │ │ live_bdr_raw │
│ {date}/       │ │to PG     │ │ live_rings_  │
│ {time}.json   │ │          │ │ raw          │
│               │ │          │ │ ring_status  │
│ RETENTION:   │ │          │ │ archive_     │
│ 3 days        │ │          │ │ entries      │
│ (auto-pruned) │ │          │ │ machine_logs │
└──────┬────────┘ └──────────┘ └──────┬───────┘
       │                              │
       ▼                              ▼
┌──────────────────────────────────────────────┐
│  API Layer (data/api.py)                     │
│                                              │
│  GET /api/old-data/search/{serial}           │
│    → queries archive_entries (PG)            │
│    → OR queries ring_status (PG)             │
│    → OR fallback scans JSON files on disk    │
│                                              │
│  POST /api/old-data/search                   │
│    → batch version (multiple serials)        │
│                                              │
│  POST /api/old-data/ingest-file              │
│    → manual file ingestion                   │
│    → writes to archive_entries + ring_status  │
│                                              │
│  Result aggregation:                         │
│    _aggregate_archive_results()              │
│    - Merges "latest" + "history" records     │
│    - Falls back to snapshot JSON if PG       │
│      has stale/zero avg_bdr                  │
│    - Returns sorted by serial, machine,      │
│      saved_at DESC                           │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Frontend (app.js — Vanilla JS SPA)          │
│                                              │
│  View: "Old Data" tab                        │
│  searchOldData()                             │
│    - Parses serials (comma/newline separated)│
│    - Fetches GET or POST /api/old-data/search│
│    - Groups results by machine               │
│    - Shows: Serial, Machine, Slot, Status,   │
│             Avg BDR, Completed Cycles,        │
│             First Seen, Last Update          │
│    - Color-coded BDR (green/warn/danger)     │
│    - Color-coded status badges               │
│    - Export to CSV                           │
└──────────────────────────────────────────────┘
```

### Key Architectural Observations

1. **Two parallel paths for the same data**: `archive_bdr_snapshot()` copies JSON files to archive AND calls the ingest API via HTTP loopback. The ingest API then writes to `archive_entries` AND `ring_status`. This means every 30s, the same data follows two redundant paths.

2. **`ring_status` is written twice** per cycle: once directly by `archive_bdr_snapshot()` calling `ingest_file_to_ring_status()`, and once by the HTTP loopback to `/api/old-data/ingest-file` which calls the same function again. Since the upsert has a `WHERE EXCLUDED.saved_at > ring_status.saved_at` guard, the duplicate write is harmless but wasteful.

3. **`live_bdr_raw` and `live_rings_raw` are not old data** — they are overwritten every cycle with only the latest snapshot. Zero historical data lives in these tables.

4. **`archive_entries` is the true historical table** — it receives one row per slot per snapshot file, with a uniqueness constraint on `(serial_number, machine, saved_at)`.

5. **JSON archive files are the raw source of truth** — but they are deleted after 3 days.

---

## PART 2 — DATABASE STRUCTURE

### Table: `archive_entries`

**Purpose:** Full historical index — each row represents one ring in one machine slot at one point in time. This is the primary table for old-data search queries.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `SERIAL` | PK | Auto-increment |
| `serial_number` | `VARCHAR(255)` | NOT NULL | Ring serial number |
| `serial_lower` | `VARCHAR(255)` | NOT NULL | Lowercased copy for case-insensitive search |
| `machine` | `VARCHAR(255)` | NULLABLE | Machine name (e.g. aqc-03) |
| `state` | `VARCHAR(50)` | NULLABLE | BDR_RUNNING, PASSED, FAILED |
| `machine_avg_bdr` | `REAL` | NULLABLE | Stored avg_bdr or aliased from avg_bdr |
| `bdr` | `REAL` | NULLABLE | Individual cycle BDR (sometimes NULL) |
| `snapshots` | `INTEGER` | NULLABLE | Always 1 (per-row counter) |
| `total_cycles` | `INTEGER` | NULLABLE | Total cycle count |
| `completed_cycles` | `INTEGER` | NULLABLE | Completed cycles |
| `start_time` | `DOUBLE PRECISION` | NULLABLE | Unix epoch of test start |
| `last_update` | `DOUBLE PRECISION` | NULLABLE | Unix epoch of last update (rarely populated) |
| `saved_at` | `VARCHAR(100)` | NULLABLE, part of UNIQUE | ISO timestamp of snapshot |
| `created_at` | `TIMESTAMP` | DEFAULT NOW() | When this DB row was inserted |
| `date` | `VARCHAR(20)` | NULLABLE | Snapshot date YYYY-MM-DD (from file path) |
| `time` | `VARCHAR(20)` | NULLABLE | Snapshot time HH:MM:SS (from file stem) |
| `slot` | `INTEGER` | NULLABLE | Slot number (1-64) |
| `battery_current` | `REAL` | NULLABLE | Battery current reading |
| `firmware_version` | `VARCHAR(100)` | NULLABLE | Firmware version string |
| `ring_mac` | `VARCHAR(50)` | NULLABLE | Bluetooth MAC address |
| `ring_name` | `VARCHAR(100)` | NULLABLE | Friendly ring name |
| `avg_bdr` | `DOUBLE PRECISION` | NULLABLE | Computed average BDR |
| `avg_bdr_is_stale` | `BOOLEAN` | NULLABLE | True if avg_bdr was replaced from fallback |
| `avg_bdr_is_estimated` | `BOOLEAN` | NULLABLE | True if avg_bdr computed from cycles vs stored |
| `stored_avg_bdr` | `DOUBLE PRECISION` | NULLABLE | Original stored avg_bdr from device firmware |
| `inter_cycle_avg_bdr` | `DOUBLE PRECISION` | NULLABLE | Inter-cycle average BDR |
| `test_start` | `DOUBLE PRECISION` | NULLABLE | Unix epoch of test start (alias for start_time) |
| `phase` | `VARCHAR(100)` | NULLABLE | Phase name (e.g. LFXO-FullSwing) |
| `cycle` | `INTEGER` | NULLABLE | Current cycle number |
| `completed_workouts` | `INTEGER` | NULLABLE | Count of completed workouts |
| `file_path` | `VARCHAR(500)` | NULLABLE | Path to original JSON archive file |

**Primary Key:** `id` (auto-increment)  
**Unique Constraint:** `(serial_number, machine, saved_at)` — prevents duplicate imports  
**Foreign Keys:** None  
**Indexes:**
- `idx_archive_serial_lower` on `(serial_lower)` — used for serial search
- `idx_archive_saved_at` on `(saved_at DESC)` — used for ordering  
**Relationships:** Each serial_number maps to multiple rows (time series). No FK relationships to other tables.  
**Retention Policy:** **NONE.** This table is never pruned. It grows unbounded.

---

### Table: `ring_status`

**Purpose:** Latest-state lookup table. One row per `(serial_number, machine)` pair holding only the most recent snapshot. Designed for fast point queries.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `serial_number` | `TEXT` | NOT NULL, PK part 1 | Ring serial |
| `machine` | `TEXT` | NOT NULL, PK part 2 | Machine name |
| `slot` | `INTEGER` | NULLABLE | Slot number |
| `ring_mac` | `TEXT` | NULLABLE | Bluetooth MAC |
| `ring_name` | `TEXT` | NULLABLE | Ring friendly name |
| `state` | `TEXT` | NOT NULL | BDR_RUNNING / PASSED / FAILED / ASSIGNED |
| `phase` | `TEXT` | NULLABLE | Current phase |
| `cycle` | `INTEGER` | NULLABLE | Current cycle number |
| `avg_bdr` | `REAL` | NULLABLE | Average BDR (only set on PASSED/FAILED) |
| `battery_current` | `REAL` | NULLABLE | Current battery reading |
| `firmware_version` | `TEXT` | NULLABLE | Firmware version |
| `phase_start_time` | `TIMESTAMPTZ` | NULLABLE | When phase started |
| `last_charge_change_time` | `TIMESTAMPTZ` | NULLABLE | Last charge state change |
| `saved_at` | `TIMESTAMPTZ` | NOT NULL | Snapshot timestamp |
| `updated_at` | `TIMESTAMPTZ` | DEFAULT now() | Row update timestamp |

**Primary Key:** `(serial_number, machine)`  
**Foreign Keys:** None  
**Indexes:** `idx_ring_serial` on `(serial_number)`  
**Relationships:** None — this is a standalone lookup table  
**Retention Policy:** **30 days.** Rows where `saved_at < NOW() - 30 days` are deleted daily.  
**Critical Design Choice:** This is **not** historical data. It is the **opposite** — it actively destroys history by keeping only the latest row per serial+machine. The `ON CONFLICT ... DO UPDATE SET WHERE EXCLUDED.saved_at > ring_status.saved_at` ensures an older snapshot can never overwrite a newer one.

---

### Table: `live_bdr_raw`

**Purpose:** Current BDR session JSON (overwritten each cycle). Not historical.

| Column | Type | Notes |
|---|---|---|
| `machine_name` | `VARCHAR(255)` PK | Machine identifier |
| `content` | `TEXT NOT NULL` | Full BDR session JSON |
| `downloaded_at` | `TIMESTAMP` | DEFAULT NOW() |

**Retention:** Rows older than 30 minutes are considered stale and force-resynced.  
**History:** **ZERO.** Only the latest snapshot exists.

---

### Table: `live_rings_raw`

**Purpose:** Current rings config JSON (overwritten each cycle). Not historical.

| Column | Type | Notes |
|---|---|---|
| `machine_name` | `VARCHAR(255)` PK | Machine identifier |
| `content` | `TEXT NOT NULL` | Full rings config JSON |
| `downloaded_at` | `TIMESTAMP` | DEFAULT NOW() |

**Retention:** Same as live_bdr_raw — 30-minute staleness window.  
**History:** **ZERO.** Only the latest snapshot exists.

---

### Table: `machine_logs`

**Purpose:** Log file metadata tracker. Records which log files were collected from which machines.

| Column | Type | Notes |
|---|---|---|
| `id` | `SERIAL PK` | Auto-increment |
| `machine_name` | `VARCHAR(255)` NOT NULL | Machine name |
| `machine_ip` | `VARCHAR(45)` | IP address |
| `fetch_time` | `TIMESTAMP` | DEFAULT NOW() |
| `file_name` | `VARCHAR(255)` NOT NULL | app.log / app.log1 |
| `file_size` | `BIGINT` | Bytes |
| `storage_location` | `TEXT NOT NULL` | Full path to stored file |
| `collection_status` | `VARCHAR(50)` | success / error |
| `error_message` | `TEXT` | Error detail |
| `created_at` | `TIMESTAMP` | DEFAULT NOW() |

**Retention:** No explicit pruning policy — grows unbounded.  
**Historical Value:** Limited — records when logs were fetched, but the log files themselves are stored on disk independently.

---

## PART 3 — WHAT EXACTLY IS STORED?

### Every Field Stored per Completed Battery Record (in `archive_entries`)

When a ring completes a BDR test (PASSED or FAILED), these fields are stored:

```
serial_number       → String, e.g. "RP-CH3-P18-WD-PG08-0000493"
serial_lower        → Lowercased copy for search
machine             → String, e.g. "aqc-03"
state               → String, "PASSED" or "FAILED" or "BDR_RUNNING"
machine_avg_bdr     → Float (aliased from avg_bdr in most cases)
bdr                 → Float (individual cycle BDR — often NULL/empty)
snapshots           → Integer (always 1 per archive_entries row)
total_cycles        → Integer, total cycle count
completed_cycles    → Integer, same as total_cycles in current code
start_time          → Double (epoch), when the test started
last_update         → Double (epoch), last update timestamp (rarely populated)
saved_at            → String, ISO timestamp of this snapshot
created_at          → Timestamp, when row was inserted into PG
date                → String, "2026-07-28" (from archive file path)
time                → String, "00-00-07" (from archive file name, hyphens not colons)
slot                → Integer, 1-64
battery_current     → Float, mA reading (can be negative = charging)
firmware_version    → String, e.g. "05.24.34.52"
ring_mac            → String, Bluetooth MAC address
ring_name           → String, e.g. "UH_F6644DCB82B7"
avg_bdr             → Float, computed average BDR
avg_bdr_is_stale    → Boolean, true if value was replaced from fallback
avg_bdr_is_estimated→ Boolean, true if computed from cycles vs stored
stored_avg_bdr      → Float OR NULL, device-reported average
inter_cycle_avg_bdr → Float OR NULL, inter-cycle average
test_start          → Double (epoch), when BDR test started
phase               → String OR NULL, e.g. "LFXO-FullSwing"
cycle               → Integer OR NULL, current cycle at snapshot time
completed_workouts  → Integer OR NULL, completed workout count
file_path           → String, local path to the JSON archive file
```

### Critical Gap in Stored Data

Fields that are **NOT stored** in any table:

| Missing Field | Why It Matters |
|---|---|
| **Battery percentage at completion** | Cannot know final battery % for completed tests |
| **Test duration** (total time) | No computed or stored test duration |
| **Pass/Fail criteria** | Not stored — only the binary state |
| **Failure reason / error code** | Not captured — just "FAILED" |
| **Discharge connect failures** | Available in live data but NOT stored in `archive_entries` |
| **Dead state** (SUSPECTED/CONFIRMED) | Available in live data but NOT stored in archives |
| **Hardware version** | Available in rings_config but NOT in archive |
| **Step statuses** | Available in live rings but NOT archived |
| **Product / Category** | Available in BDR session JSON (`product` field) but not extracted |
| **Battery category** | Not stored — computed by frontend from serial number |
| **Battery history** (time series) | Stored in JSON files but NOT in `archive_entries` |
| **Charger state** (on/off) | Available from charger-status API but NOT archived |
| **Charging current** | Available in live data but NOT in `archive_entries` |
| **Operator/machine user** | Not tracked anywhere |
| **Ambient temperature** | Not measured |
| **Cycle-level details** | Per-cycle start%, end%, duration, BDR — NOT in archive_entries |

---

## PART 4 — HISTORY RETENTION

### When a Battery Passes

```
Battery finishes BDR test (state = "PASSED")
  ↓
Next download cycle (≤30s):
  ↓
1. JSON written to DESTINATION/bdr/{machine}.json (overwrites)
2. archive_bdr_snapshot() copies to:
     DESTINATION/archive/{machine}/{date}/{time}.json
   (rate-limited to once per 30s)
3. ring_status upserted with latest data
4. HTTP POST /api/old-data/ingest-file called
   → archive_entries INSERT (one row per slot in the snapshot)
```

### When Battery Removed from Machine

```
Battery removed from slot
  ↓
Next download cycle:
  ↓
bdr_session.json no longer contains that serial in that slot
  ↓
JSON file written without that slot data
  ↓
ring_status: row still exists (serial_number+machine PK preserved)
  BUT the row is never deleted for removal — it just shows the last known state
  ↓
archive_entries: the last snapshot still exists with that serial
  ↓
live_bdr_raw: slot may now show empty or different serial
```

**Critical behavior:** `ring_status` has **no row deletion on removal**. If a ring is removed from a machine, its `ring_status` row persists with the last known state. If the same serial reappears in a different machine, a new `(serial, machine)` row is inserted. The old machine row remains.

### When Slot Reused

```
Old ring removed from slot 5
  ↓
New ring inserted into slot 5 (different serial)
  ↓
Next download cycle:
  ↓
bdr JSON now shows new serial in slot 5
  ↓
archive_entries already has the old serial's entry with that (serial, machine, saved_at)
  → Uniqueness constraint prevents conflict (different serial)
  ↓
ring_status: new (serial, machine) row upserted — no conflict (different serial)
  ↓
live_bdr_raw: slot 5 content overwritten with new serial
```

**Old record remains:** YES. The old `archive_entries` row for the previous serial is preserved. `ring_status` also preserves the old record because the primary key is `(serial_number, machine)` — the new ring has a different serial.

### Retention Summary

| Storage Location | Retention Period | Pruning Mechanism |
|---|---|---|
| `DESTINATION/archive/{machine}/{date}/{time}.json` | **3 days** (`api.py:218`, default param says 7 but called with 3) | `_prune_old_archive_files(days=3)` runs daily in background thread. Files older than 3 days by mtime are deleted. |
| `archive_entries` (PostgreSQL) | **FOREVER** (no pruning) | No deletion mechanism exists. Grows unbounded. |
| `ring_status` (PostgreSQL) | **30 days** | `DELETE WHERE saved_at < NOW() - INTERVAL '30 days'` runs daily. |
| `live_bdr_raw` (PostgreSQL) | **30 minutes** (data considered stale and force-resynced) | Overwritten every cycle. Stale data deleted then re-synced. |
| `live_rings_raw` (PostgreSQL) | **30 minutes** | Same as live_bdr_raw. |
| `machine_logs` (PostgreSQL) | **Forever** | No pruning. |
| SQLite `archive.db` | **Unknown/N/A** | Legacy — being migrated. No documented pruning. |

**Key finding:** The only long-term historical storage is `archive_entries`, which has no retention limit. Everything else short-lived or non-historical.

---

## PART 5 — EVENT HISTORY

### Does the System Store Events?

| Event | Stored? | Where? | Notes |
|---|---|---|---|
| **Battery inserted into slot** | NO | Nowhere | No insertion event recorded. Only visible as "serial_number first appears in archive_entries" — but no explicit event. |
| **Battery started test** | NO | Nowhere | State transition from ASSIGNED → BDR_RUNNING is not recorded as an event. You can infer it from archive_entries if snapshots cover the transition. |
| **Battery paused** | NO | Nowhere | No pause event exists in the data model. |
| **Battery resumed** | NO | Nowhere | No resume event. |
| **Battery passed** | IMPLICIT | `archive_entries.state = "PASSED"` | Only the final state is stored. The exact moment of passing is not recorded as a distinct event — you only know the state of the snapshot. |
| **Battery failed** | IMPLICIT | `archive_entries.state = "FAILED"` | Same as passed — final state only, no event timestamp. |
| **Battery removed from slot** | NO | Nowhere | No removal event. The ring simply stops appearing in new snapshots. You can infer removal time from "last seen" but only approximately (≤30s resolution) if you scan all snapshots. |
| **New battery inserted** | NO | Nowhere | Same as removal — only visible as "serial_number changes in slot between snapshots." |
| **Charger turned ON** | NO | Nowhere | Not tracked historically. |
| **Charger turned OFF** | NO | Nowhere | Not tracked historically. |
| **AWM started** | NO | Nowhere | AWM commands are fire-and-forget with no persistence. |
| **AWM stopped** | NO | Nowhere | Same as above. |
| **Firmware updated** | NO | Nowhere | Firmware version is stored per snapshot, so a change is visible. But no update event is recorded. |
| **Data download** | PARTIAL | `machine_logs` | Log file downloads are recorded. BDR/rings downloads are not recorded as events. |
| **Error/failure event** | NO | Nowhere | Only the FAILED state is stored. Error messages are in live data but not in archive_entries. |

### What Events Are Missing

**ALL discrete events are missing.** The system does not store any of these:

- `ring_inserted` — timestamp, slot, machine
- `ring_removed` — timestamp, slot, machine  
- `test_started` — timestamp, phase
- `test_paused` — timestamp
- `test_resumed` — timestamp
- `test_completed` — timestamp, result
- `charger_on` — timestamp, slot
- `charger_off` — timestamp, slot
- `awm_start` — timestamp, slot
- `awm_stop` — timestamp, slot
- `error_occurred` — timestamp, error type, slot
- `firmware_update` — timestamp, old/new version
- `machine_offline` — timestamp
- `machine_online` — timestamp
- `slot_cleared` — timestamp

**The system only stores state snapshots at regular 30-second intervals.** Events must be **inferred** by comparing consecutive snapshots — which is only possible if:
1. JSON archive files are still available (≤3 days old)
2. You can scan all snapshots for a given serial

After 3 days, only `archive_entries` remains, and it cannot reconstruct events because the 30-second snapshot resolution loses the exact transition between states.

---

## PART 6 — TIMESTAMPS

### Timestamps That Exist

| Timestamp | Table(s) | Format | Notes |
|---|---|---|---|
| `saved_at` | archive_entries, ring_status, BDR JSON, archive JSON | ISO 8601 string (`"2026-07-28T00:00:06.434008+05:30"`) | The primary temporal anchor. Recorded from the device's bdr_session.json at download time. |
| `downloaded_at` | live_bdr_raw, live_rings_raw | `TIMESTAMP` with timezone | When the data was downloaded from the machine. |
| `created_at` | archive_entries, machine_logs | `TIMESTAMP` with timezone | When the database row was inserted. |
| `updated_at` | ring_status | `TIMESTAMPTZ` | When the ring_status row was last upserted. |
| `start_time` | archive_entries | `DOUBLE PRECISION` (Unix epoch) | When the BDR test started. From `bdr_data.test_start`. |
| `test_start` | archive_entries | `DOUBLE PRECISION` (Unix epoch) | Alias/duplicate of start_time. |
| `last_update` | archive_entries | `DOUBLE PRECISION` (Unix epoch) | Last update time — rarely populated, often 0 or NULL. |
| `fetch_time` | machine_logs | `TIMESTAMP` | When logs were fetched. |
| `phase_start_time` | ring_status | `TIMESTAMPTZ` | When the current phase started. |
| `last_charge_change_time` | ring_status | `TIMESTAMPTZ` | When charge state last changed (BDR_RUNNING only). |
| `fetch_time` | machine_logs | `TIMESTAMP` | When a log file was collected. |
| File mtime | archive JSON files on disk | File system timestamp | Used by pruner — not directly available via API. |

### Timestamps That Exist in Live BDR JSON But NOT in archive_entries

- `bdr_battery_history[][0]` — Timestamps of each battery measurement (stored in JSON files but not extracted to archive_entries)
- `bdr_data.cycles[].start_pct` — Per-cycle start times (epoch), not stored in archive_entries

### Timestamps That Do NOT Exist Anywhere

| Missing Timestamp | Impact |
|---|---|
| **Test completion timestamp** | Cannot determine when exactly a test passed or failed. Only snapshot time is available, which may be up to 30s after the actual event. |
| **Ring insertion timestamp** | Cannot determine when a ring was placed in a slot. |
| **Ring removal timestamp** | Cannot determine when a ring was removed. |
| **Charger event timestamps** | Cannot correlate charge events with test results. |
| **Error occurrence timestamp** | Error state may have occurred minutes before the next snapshot captured it. |
| **Operator timestamp** | No human interaction timestamps. |
| **Machine boot/restart timestamp** | No machine lifecycle tracking. |

---

## PART 7 — SHIFT ANALYSIS

### Can the Current System Answer Shift Questions WITHOUT Changes?

| Question | Can Answer? | How / Why Not |
|---|---|---|
| **How many passed this shift?** | PARTIAL | If you define a shift as a time window (e.g. 8AM-4PM), you can query `archive_entries WHERE state = 'PASSED' AND saved_at BETWEEN ...`. But: (1) `saved_at` is VARCHAR, not TIMESTAMP, making range queries inefficient. (2) Multiple snapshots of the same ring exist — the same PASSED ring may appear in dozens of snapshots within the shift, massively inflating counts. (3) No explicit "test completed" event means you can't distinguish "still running" from "just passed." |
| **How many failed this shift?** | PARTIAL | Same problems as passed count. State changes from PASSED → FAILED don't create new rows — the state just updates in the next snapshot. |
| **Pass rate this morning?** | PARTIAL | Same issue: snapshot count ≠ test count. Need to deduplicate by serial+test session, which is not possible because test sessions are not identified. |
| **Night shift report?** | PARTIAL | Same issue. Temporal filtering works but deduplication does not. |
| **8AM–4PM report?** | PARTIAL | Same. |
| **Yesterday's production?** | PARTIAL | JSON archive files for yesterday exist (if not pruned) and contain per-slot data. The API can search by serial but not by completion time window. |
| **Weekly production?** | NO | JSON files older than 3 days are pruned. `archive_entries` may have the data, but no aggregation endpoint exists — you'd need to query all rows and deduplicate manually. |
| **Monthly production?** | PARTIAL | `archive_entries` may cover a month. Same deduplication problem. No aggregation query exists. |

### Why Shift Analysis Is Fundamentally Limited

1. **No test completion events** — The system captures snapshots, not completions. One test → dozens of snapshot rows.
2. **No unique test session ID** — Cannot group rows belonging to the same test instance.
3. **`saved_at` is VARCHAR** — Not a proper TIMESTAMP. Range queries use string comparison.
4. **No aggregation endpoints** — The only old-data endpoint is per-serial search. There is no "get all PASSED records in time range" API.
5. **Frontend shows only latest per machine** — Grouped results in the UI show only the latest snapshot per machine, losing historical per-slot perspective.

---

## PART 8 — MACHINE HISTORY

### Can AI Answer Machine-Level Questions?

| Question | Can Answer? | Explanation |
|---|---|---|
| **Machine 12's last week performance** | PARTIAL | If `archive_entries` has sufficient data (depends on migration completeness): query by machine name across time range. But: same deduplication problem — multiple rows per test. No pre-computed machine KPIs. |
| **Last month's failures** | PARTIAL | Same. You could count distinct serials with FAILED state. But a ring that failed and was retested would appear as PASSED in later snapshots — the failure count would be wrong because the state changes. |
| **Average BDR** | PARTIAL | You can compute avg(avg_bdr) for a machine. But this includes BDR_RUNNING rows (which have NULL avg_bdr) and multiple rows per test. The result would be misleading unless properly deduplicated. |
| **Battery trend** | LIMITED | No per-serial time series aggregation. You'd need to export all rows and group by serial+date, which has no API support. |
| **Health trend** | LIMITED | No health metric stored — only raw avg_bdr. Health is computed in the frontend via heatmap thresholds. Not accessible historically. |
| **Failure trend** | LIMITED | No failure rate computation endpoint. Raw data exists but requires client-side aggregation. |
| **Recurring issues** | NO | No failure categorization. No error codes. No pattern tracking. The system only knows PASSED or FAILED. |

### Why Machine History Is Insufficient

1. **`archive_entries` has no machine-level aggregation** — Only per-serial search exists.
2. **`ring_status` is NOT historical** — It only has latest state per (serial, machine).
3. **`live_bdr_raw` overwrites** — Zero history for the current snapshot.
4. **No machine-level time series** — avg_bdr per machine per day would require a custom query that doesn't exist.
5. **The API returns `machine_avg_bdr` but it's per-slot, not per-machine** — The name is misleading; it's actually `slot.avg_bdr`.

---

## PART 9 — SLOT HISTORY

### Can AI Answer Slot-Level Questions?

| Question | Can Answer? | Explanation |
|---|---|---|
| **How many batteries tested in slot 12?** | PARTIAL | `archive_entries` has slot data. You can count DISTINCT serial_number WHERE slot=12. But: the same ring returning to slot 12 would be counted twice. No API for this — requires raw SQL. |
| **How many passed vs failed?** | PARTIAL | You could query by slot+state. But: snapshot duplication — one test creates dozens of rows. Need to collapse by serial+test_session, but test sessions aren't identified. |
| **Average BDR** | PARTIAL | avg(avg_bdr) for slot 12. But includes running (NULL) and multiple measurements per test. |
| **Average battery %** | NO | Battery % is in the JSON `bdr_battery_history` but NOT in `archive_entries`. |
| **Failure history** | PARTIAL | Same deduplication problem. |
| **Replacement frequency** | NO | No insertion/removal events. You can approximate by watching serial changes across snapshots, but only in JSON archive files (≤3 days). |

### Why Slot History Is Insufficient

1. **No slot-level time series table** — Slot performance over time requires scanning `archive_entries` and grouping.
2. **`archive_entries` does not capture slot-specific events** — No "ring inserted into slot" or "ring removed from slot" records.
3. **`ring_status` overwrites per (serial, machine)** — If a ring moves from slot 5 to slot 12 on the same machine, the old slot assignment is lost.
4. **The frontend only shows latest slot data** — The Old Data view shows latest per machine, not slot-level drill-down.

---

## PART 10 — CATEGORY HISTORY

### Can AI Answer Category-Level Questions?

| Question | Can Answer? | Explanation |
|---|---|---|
| **AIR historical performance** | NO | Category is NOT stored in `archive_entries`. It's computed on the frontend by `classifySerial()` in app.js. No API endpoint computes category aggregates. The raw serial numbers exist in the database, so category CAN be derived, but no backend support exists. |
| **PRO pass rate** | NO | Same — no category field in database. |
| **LUX failure rate** | NO | Same. |
| **RT Conversion trend** | NO | Same. |
| **Wabi Sabi average BDR** | NO | Same. |
| **Category comparison** | NO | No aggregation endpoint by category. |
| **Weekly category comparison** | NO | No category field + no weekly aggregation + no time-series grouping. |

### Why Category History Is Completely Unavailable

1. **Category is NOT persisted in any database** — The `classifySerial()` function runs only in the browser.
2. **No backend endpoint computes category metrics** — The classification logic exists in `app.js` only.
3. **The `product` field** in BDR session JSON says "PRO" for PRO batteries, but:
   - It's NOT extracted into `archive_entries`
   - It's NOT stored for other categories (AIR, LUX, RT, Wabi Sabi)
   - It only covers a subset of batteries
4. **SKU and category breakdowns** are computed on-the-fly in the Data Visualization view — only for data currently in memory.

---

## PART 11 — DATA QUALITY

### Missing Fields

| Field | Location | Missing From |
|---|---|---|
| `battery_current` | Often NULL | `archive_entries` allows NULL |
| `stored_avg_bdr` | Often NULL | Only present in PASSED/FAILED bdr_data |
| `inter_cycle_avg_bdr` | Often NULL | Same |
| `completed_workouts` | Often NULL | `ring_status` returns NULL always |
| `hardware_version` | rings_config | NOT in any database table |
| `product` / `category` | BDR JSON | NOT extracted |
| `error` / `error_message` | rings_config | NOT in archive |
| `dead_state` | rings_config | NOT in archive_entries |
| `discharge_connect_failures` | rings_config | NOT in archive_entries |
| `charging_current_ma` | BDR JSON | NOT in archive_entries |

### Missing Timestamps

(Detailed in Part 6 above)

### Duplicate Risk

| Risk Area | Explanation |
|---|---|
| **`archive_entries` UNIQUE constraint** | `(serial_number, machine, saved_at)` prevents true duplicates. However, the same snapshot file ingested twice would insert duplicate rows if `saved_at` differs slightly. |
| **`ring_status` upsert** | The `WHERE EXCLUDED.saved_at > ring_status.saved_at` guard prevents older data from overwriting newer. But if two concurrent ingestions happen, the last one wins — there's no merge logic. |
| **JSON archive files** | `archive_bdr_snapshot()` copies files every 30s. If the download layer creates the same file twice, the second copy silently overwrites the first (which is fine — they're identical). |
| **Multiple snapshots per second** | 2064 files in aqc-03's 2026-07-28 directory means ~1 snapshot every 42 seconds on average. Each snapshot creates one archive_entries row per occupied slot. |

### Data Inconsistency

| Issue | Details |
|---|---|
| **avg_bdr fallback logic** | `_calc_avg_bdr()` uses stored avg_bdr first; if NULL/zero/negative, computes from completed_cycles. This means the same slot can have avg_bdr from different sources at different times. The `avg_bdr_is_estimated` flag tracks this but is often not propagated correctly through the aggregation pipeline. |
| **Zero-value avg_bdr** | `0.0` is treated as "bad data" (see `_aggregate_archive_results` line 1262: `avg == 0.0` is treated as stale). This means a real avg_bdr of 0.0 would be silently replaced with a fallback. |
| **Negative avg_bdr** | Same as zero — treated as "null or bad" and replaced with fallback. |
| **machine_avg_bdr aliasing** | The field is named "machine_avg_bdr" but it's actually per-slot avg_bdr. Misleading naming. |
| **completed_cycles vs total_cycles** | Currently set to the same value (`max(len(completed_cycles), len(bdr_data.cycles))`). They are redundant. |
| **saved_at is VARCHAR** | ISO strings with timezone offsets. Comparisons use string ordering, which works for ISO 8601 but is fragile. PostgreSQL TIMESTAMPTZ would be better. |

### Data Loss Risk

| Risk | Details |
|---|---|
| **JSON archive file pruning** | Files deleted after 3 days. `archive_entries` in PG should preserve the data, but (1) the ingest may fail silently, and (2) the `bdr_battery_history` time series is ONLY in the JSON files — never extracted to PG. |
| **Ingest failure is silent** | `archive_bdr_snapshot()` calls the ingest API with `urllib.request.urlopen(req, timeout=5)` and catches ALL exceptions with `except Exception: pass`. If PG is down, the data in JSON files is lost after 3 days. |
| **`ring_status` 30-day pruning** | After 30 days, `ring_status` rows are deleted. The only remaining record would be in `archive_entries` — but the full snapshot data (battery history, cycles) is gone. |
| **No archive_entries pruning** | This table grows unbounded. No retention policy. No archival strategy. Risk of disk exhaustion over years. |

### Race Conditions

| Scenario | Risk |
|---|---|
| **Download + archive + ingest** | All happen in sequence but not atomically. If the process crashes between JSON file copy and PG ingest, data is lost. |
| **Concurrent ingest of same file** | The `UNIQUE (serial_number, machine, saved_at)` prevents true duplicates, but two parallel processes could each insert different data for the same key — unlikely with current single-threaded design but possible if multiple bg loops run. |
| **Prune vs archive** | Pruner could delete an archive file while ingest is reading it. The `except OSError: continue` in the ingest path handles this silently. |

### Retention Problems

(Detailed in Part 4 above)

### Import Problems

| Problem | Details |
|---|---|
| **Migration completeness** | SQLite → PG migration may be incomplete. Backfill chunk files (000000-002000) exist but coverage is unknown. |
| **No idempotency on re-import** | The `ON CONFLICT DO NOTHING` prevents duplicates by unique key, but if the same data is imported with a different `saved_at`, a new row is inserted. |
| **No validation** | Corrupted JSON files are silently skipped. No audit log of failed imports. |

### Historical Limitations

| Limitation | Impact |
|---|---|
| **Data starts from unknown date** | No timeline of when data collection began. Migration backups are dated Jul 2026. |
| **No manufacturing date** | Cannot age batteries. |
| **No batch/lot tracking** | Cannot trace quality to production batches. |
| **No operator tracking** | Cannot analyze human factors. |
| **No environmental data** | Temperature/humidity not captured. |

---

## PART 12 — AI READINESS

### Battery Intelligence Center — Can Current Old Data Support These Features?

| Feature | Can Support? | Explanation |
|---|---|---|
| **Executive Summary** | NO | No aggregation endpoints. No KPI pre-computation. An "executive summary" would require totals, averages, pass rates, trends — none of which are queryable via the existing API. |
| **Shift Report** | NO | (See Part 7) No test completion events, no session IDs, no shift-level aggregation. |
| **Daily Report** | PARTIAL | Could approximate from `archive_entries` with raw SQL, but the API only supports per-serial search. No "daily summary" endpoint exists. Duplicate snapshots inflate counts. |
| **Weekly Report** | PARTIAL | Same as daily report, but compounded by the 3-day JSON prune window and the 30-day ring_status prune. |
| **Monthly Report** | PARTIAL | `archive_entries` may have the raw data, but no aggregation mechanism exists. Raw query would need to deduplicate serials by session — impossible without session IDs. |
| **Machine Ranking** | PARTIAL | Raw data exists to compute per-machine avg_bdr and pass rates. But: no aggregation endpoint, deduplication problem, misleading machine_avg_bdr alias. |
| **Category Ranking** | NO | Category not stored in any database. Classification only in frontend JS. |
| **Trend Analysis** | LIMITED | Time-series data exists in `archive_entries` but: (1) no trend computation endpoint, (2) duplicate snapshots mask real trends, (3) no moving average or aggregation queries available. |
| **Recommendations** | NO | No predictive models. No threshold system. No rule engine. |
| **Predictions** | NO | No ML pipeline. No feature store. No model serving. The data format (snapshot-centric, session-opaque) is not ML-ready. |
| **AI Chat** | NO | No natural language interface. No vector embeddings. No context store. The old-data search API only handles exact serial lookups. |
| **Historical Queries** | PARTIAL | Per-serial search works well for finding a specific ring. But: (1) no free-text search, (2) no range queries, (3) no aggregate queries, (4) no cross-serial analysis. |

---

## PART 13 — IF NOT: MINIMUM CHANGES REQUIRED

Since the current implementation is insufficient for an Enterprise Battery Intelligence platform, here are the **absolute minimum** changes required — without redesigning the architecture, changing APIs, workflows, frontend, databases, or creating new tables.

### 13.1 Add These Fields to `archive_entries`

| Field | Type | Reason |
|---|---|---|
| `category` | `VARCHAR(20)` | Persist the battery category (AIR/PRO/LUX/RT/WABI SABI) at ingestion time. The `classifySerial()` logic from app.js would move to the backend. |
| `test_duration_seconds` | `INTEGER` | Compute and store total test duration from `test_start` to finalization. |
| `test_completed_at` | `VARCHAR(100)` | The `saved_at` value of the first snapshot where state became PASSED/FAILED (actual completion time, not continuing snapshot time). |
| `discharge_connect_failures` | `INTEGER` | Persist this field from the slot data. |
| `dead_state` | `VARCHAR(20)` | Persist dead_state from slot data. |
| `battery_pct_at_completion` | `REAL` | Extract final battery % from bdr_battery_history at completion time. |

**These are additive — no schema migration would break existing rows.**

### 13.2 Track One Additional Field in the BDR JSON

The `bdr_session.json` already contains `bdr_data.cycles[].battery_pct` and `battery_current` data. The only thing missing in the BDR JSON that would help is a **test session ID** — but that requires device-side changes, which is out of scope.

### 13.3 No Changes Required To:

- Database architecture (PostgreSQL stays)
- API endpoints (existing endpoints continue to work)
- Frontend (no UI changes)
- Workflows (download → archive → ingest remains the same)
- Data collection (SSH/SFTP stays)
- JSON file format (unchanged)

### 13.4 Changes Required to Ingestion Logic (in `_make_archive_entry`)

The `_make_archive_entry()` function at `api.py:987-1012` would be extended to extract and store the additional fields listed in 13.1. No new functions. No new code paths. Just enriching the existing archive entry with data already present in the slot JSON.

The `classifySerial()` function (currently only in `app.js:966-980`) would be ported to Python and called during ingestion.

---

## PART 14 — FINAL VERDICT

### Ratings (Scale: 1-10)

| Dimension | Score | Explanation |
|---|---|---|
| **Historical Data** | 4/10 | `archive_entries` stores snapshot data indefinitely, but: no test completion events, no session tracking, no category persistence, no battery history time series, limited field coverage. JSON source files deleted after 3 days. |
| **Shift Analytics** | 1/10 | Fundamentally impossible without test completion events. Snapshot-centric design cannot answer "how many tests completed in a time window." No aggregation endpoints. |
| **Reporting** | 2/10 | Per-serial search is the only query path. No summary reports, no aggregations, no date-range queries, no KPI endpoints. |
| **AI Readiness** | 3/10 | Raw data exists but is not ML-ready. Features would need to be engineered from scratch. Duplicate snapshots, inconsistent avg_bdr reporting, missing critical fields. |
| **Prediction Readiness** | 1/10 | No labeled training data structure. No feature store. No model serving. The data model is designed for human lookup, not ML. |
| **Trend Readiness** | 2/10 | Time-series data exists but cannot be queried as a trend. No grouping by time window. No moving computations. |
| **Knowledge Base Readiness** | 1/10 | No semantic structure. No entity relationships. No natural language access. |

### Final Verdict

**"If you were the lead AI architect, would you start implementing the AI module now?"**

**NO.**

### Exactly What Is Missing

The Old Data system is a **snapshot archive**, not a **test history database**. Every design decision optimizes for "find the latest state of a specific serial number" — which is excellent for debugging a single ring but completely unsuitable for enterprise analytics.

The fundamental problems are:

1. **No test completion events.** You cannot count tests. You cannot compute pass rates. You cannot build shift reports. Every "test completed" must be inferred by comparing consecutive snapshots — and even then, a single test generates dozens of snapshot rows.

2. **No unique test session identifier.** Multiple snapshots of the same ongoing test cannot be grouped. A PASSED ring generates new archive_entries rows every 30 seconds until it's removed. There is no way to collapse these into one "test result."

3. **Category is not persisted.** The classification logic exists only in the frontend JavaScript. No backend can answer "how many PRO batteries passed today?" without reimplementing the classification or extracting it at ingest time.

4. **Key diagnostic fields are missing from the archive.** `battery_pct`, `discharge_connect_failures`, `dead_state`, `error_code` — these exist in the live data but are not stored in `archive_entries`. After 3 days (when JSON files are pruned), they are lost forever.

5. **The only query access pattern is per-serial lookup.** There is no API to:
   - Get all tests completed in a date range
   - Get pass/fail counts by machine or slot
   - Get average BDR trends over time
   - Compare categories
   
   Every enterprise analytics feature would require either new API endpoints or direct SQL access to the database — which is not available through the existing architecture.

### What Would It Take to Change This Answer

Add **four things** to the existing architecture (without redesign):

1. **Deduplicate at ingest time** — When a ring's state becomes PASSED/FAILED, emit one "test completed" record instead of continuing to snapshot it. This is a change to `archive_bdr_snapshot()` or the ingest logic: skip snapshotting slots whose state hasn't changed since the last sync.

2. **Extract category at ingest** — Port `classifySerial()` from app.js to Python. Call it in `_make_archive_entry()` and store the result in a new `category` column.

3. **Extract existing diagnostic fields** — `discharge_connect_failures`, `dead_state`, and the last `battery_pct` from `bdr_battery_history` are already in the slot JSON. Store them in `archive_entries`.

4. **Add one search-serial-by-date-range endpoint** — `GET /api/old-data/search?state=PASSED&from=...&to=...` — single new API endpoint, no schema change, enables shift reports.

These changes would bring the readiness from 3/10 to approximately 6/10 — sufficient for basic enterprise analytics without a ground-up redesign.
