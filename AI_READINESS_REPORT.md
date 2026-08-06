# AI Data Dictionary & Analytics Readiness Report

**Project:** BDR Dashboard  
**Date:** 2026-07-28  
**Version:** 2.0.0  

---

## SECTION 1 — Database Tables

### 1.1 `live_bdr_raw` (PostgreSQL)

**Purpose:** Stores the latest BDR session JSON snapshot for each machine. One row per machine, overwritten on each sync cycle.

| Column | Type | Notes |
|---|---|---|
| `machine_name` | `VARCHAR(255)` PK | e.g. aqc-03 |
| `content` | `TEXT NOT NULL` | Full BDR session JSON body |
| `downloaded_at` | `TIMESTAMP NOT NULL` | `DEFAULT NOW()` |

**Primary Key:** `machine_name`  
**Foreign Keys:** None  
**Relationships:** Joins logically with `machines.json` config by name  
**Timestamp Fields:** `downloaded_at` — set on each UPSERT  
**Retention:** Rows older than 30 minutes are considered stale and force-resynced

---

### 1.2 `live_rings_raw` (PostgreSQL)

**Purpose:** Stores the latest rings_config JSON snapshot for each machine. One row per machine, overwritten on each sync cycle.

| Column | Type | Notes |
|---|---|---|
| `machine_name` | `VARCHAR(255)` PK | e.g. aqc-03 |
| `content` | `TEXT NOT NULL` | Full rings_config JSON body |
| `downloaded_at` | `TIMESTAMP NOT NULL` | `DEFAULT NOW()` |

**Primary Key:** `machine_name`  
**Foreign Keys:** None  
**Relationships:** Joins logically with `machines.json` config by name  
**Timestamp Fields:** `downloaded_at`  
**Retention:** Same 30-minute staleness window as `live_bdr_raw`

---

### 1.3 `ring_status` (PostgreSQL)

**Purpose:** Latest-state lookup table for fast search by serial number. One row per `(serial_number, machine)` — always holds the most recent snapshot data.

| Column | Type | Notes |
|---|---|---|
| `serial_number` | `TEXT NOT NULL` | PK part 1 — ring serial |
| `machine` | `TEXT NOT NULL` | PK part 2 — machine name |
| `slot` | `INTEGER` | Slot number (1-64) |
| `ring_mac` | `TEXT` | Bluetooth MAC address |
| `ring_name` | `TEXT` | Friendly ring name |
| `state` | `TEXT NOT NULL` | BDR_RUNNING / PASSED / FAILED / ASSIGNED |
| `phase` | `TEXT` | E.g. "LFXO-FullSwing" |
| `cycle` | `INTEGER` | Current BDR cycle number |
| `avg_bdr` | `REAL` | Average BDR value (only populated on PASSED/FAILED) |
| `battery_current` | `REAL` | Battery current reading |
| `firmware_version` | `TEXT` | Firmware version string |
| `phase_start_time` | `TIMESTAMPTZ` | When current phase started (epoch → timestamp) |
| `last_charge_change_time` | `TIMESTAMPTZ` | Last charge state change (BDR_RUNNING only) |
| `saved_at` | `TIMESTAMPTZ NOT NULL` | Snapshot timestamp |
| `updated_at` | `TIMESTAMPTZ` | `DEFAULT now()` — row update time |

**Primary Key:** `(serial_number, machine)`  
**Foreign Keys:** None  
**Indexes:** `idx_ring_serial` on `serial_number`  
**Relationships:** Each row maps 1:1 to a unique ring in a unique machine slot  
**Timestamp Fields:** `phase_start_time`, `last_charge_change_time`, `saved_at`, `updated_at`  
**Retention:** Rows older than 30 days are pruned daily

---

### 1.4 `archive_entries` (PostgreSQL)

**Purpose:** Historical search index. Contains snapshots of every ring across all machines at various points in time. Append-only; used for old-data search by serial number.

| Column | Type | Notes |
|---|---|---|
| `id` | `SERIAL PK` | Auto-increment |
| `serial_number` | `VARCHAR(255) NOT NULL` | Ring serial number |
| `serial_lower` | `VARCHAR(255) NOT NULL` | Lowercased copy for search |
| `machine` | `VARCHAR(255)` | Machine name |
| `state` | `VARCHAR(50)` | BDR_RUNNING / PASSED / FAILED |
| `machine_avg_bdr` | `REAL` | Average BDR (stored or computed) |
| `bdr` | `REAL` | Individual cycle BDR |
| `snapshots` | `INTEGER` | Count of snapshots |
| `total_cycles` | `INTEGER` | Total cycle count |
| `completed_cycles` | `INTEGER` | Completed cycle count |
| `start_time` | `DOUBLE PRECISION` | Unix epoch of test start |
| `last_update` | `DOUBLE PRECISION` | Unix epoch of last update |
| `saved_at` | `VARCHAR(100)` | ISO timestamp of snapshot |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` — DB insert time |
| `date` | `VARCHAR(20)` | Snapshot date (YYYY-MM-DD) |
| `time` | `VARCHAR(20)` | Snapshot time (HH:MM:SS) |
| `slot` | `INTEGER` | Slot number |
| `battery_current` | `REAL` | Battery current reading |
| `firmware_version` | `VARCHAR(100)` | Firmware version |
| `ring_mac` | `VARCHAR(50)` | Bluetooth MAC |
| `ring_name` | `VARCHAR(100)` | Ring name |
| `avg_bdr` | `DOUBLE PRECISION` | Computed avg BDR |
| `avg_bdr_is_stale` | `BOOLEAN` | Whether avg_bdr may be stale |
| `avg_bdr_is_estimated` | `BOOLEAN` | Whether avg_bdr was estimated from completed cycles |
| `stored_avg_bdr` | `DOUBLE PRECISION` | Original stored avg_bdr from device |
| `inter_cycle_avg_bdr` | `DOUBLE PRECISION` | Inter-cycle average BDR |
| `test_start` | `DOUBLE PRECISION` | Test start epoch |
| `phase` | `VARCHAR(100)` | Current phase |
| `cycle` | `INTEGER` | Current cycle |
| `completed_workouts` | `INTEGER` | Count of completed workouts |
| `file_path` | `VARCHAR(500)` | Path to original JSON file |

**Primary Key:** `id`  
**Unique Constraint:** `(serial_number, machine, saved_at)`  
**Foreign Keys:** None  
**Indexes:** `idx_archive_serial_lower` on `serial_lower`, `idx_archive_saved_at` on `saved_at DESC`  
**Relationships:** Multiple rows per `(serial_number, machine)` — represents time series  
**Timestamp Fields:** `start_time`, `last_update`, `saved_at`, `created_at`

---

### 1.5 `machine_logs` (PostgreSQL)

**Purpose:** Log file metadata tracking — records files collected from remote machines.

| Column | Type | Notes |
|---|---|---|
| `id` | `SERIAL PK` | Auto-increment |
| `machine_name` | `VARCHAR(255) NOT NULL` | Machine name |
| `machine_ip` | `VARCHAR(45)` | IP address |
| `fetch_time` | `TIMESTAMP` | `DEFAULT NOW()` |
| `file_name` | `VARCHAR(255) NOT NULL` | Log filename |
| `file_size` | `BIGINT` | File size in bytes |
| `storage_location` | `TEXT NOT NULL` | Path to stored file |
| `collection_status` | `VARCHAR(50)` | success / error |
| `error_message` | `TEXT` | Error details if failed |
| `created_at` | `TIMESTAMP` | `DEFAULT NOW()` |

**Primary Key:** `id`  
**Foreign Keys:** None  
**Indexes:** `idx_machine_logs_fetch_time`, `idx_machine_logs_machine_name`  
**Timestamp Fields:** `fetch_time`, `created_at`

---

### 1.6 SQLite `archive.db`

**Purpose:** Legacy historical archive (11.4 GB). Being migrated to PostgreSQL `archive_entries`. Same schema as PostgreSQL version. Contains backfill chunks and historical search data.

**Note:** This is an append-only database with the same schema as PostgreSQL `archive_entries`. It exists primarily for historical compatibility and migration purposes.

---

## SECTION 2 — API Endpoints

### 2.1 Live Data Endpoints

#### `GET /api/health`
| Field | Description |
|---|---|
| **Request** | None |
| **Response** | `{"status": "healthy"|"degraded", "last_successful_sync": <epoch>, "postgres_available": bool}` |
| **Data Returned** | Health status, last sync timestamp, PG availability |
| **Refresh Interval** | On-demand (no cache) |

#### `GET /api/machines`
| Field | Description |
|---|---|
| **Request** | None |
| **Response** | `{"machines": ["aqc-03", "aqc-04", ...]}` |
| **Data Returned** | Sorted list of all machine names from PG ∪ config ∪ files |
| **Refresh Interval** | On-demand (no cache) |

#### `GET /api/bdr`
| Field | Description |
|---|---|
| **Request** | None |
| **Response** | `{ "machine_name": { "saved_at": "...", "slots": {...} }, ... }` |
| **Data Returned** | All BDR session data (every machine, every slot, every field) |
| **Refresh Interval** | 5-second in-memory cache TTL. Backend syncs from files every 30s |

#### `GET /api/bdr/{machine}`
| Field | Description |
|---|---|
| **Request** | Machine name path param |
| **Response** | `{ "saved_at": "...", "slots": { "1": {...}, ... } }` |
| **Data Returned** | BDR session data for a single machine |
| **Refresh Interval** | No cache — reads PG (30-min window), falls back to JSON file |

#### `GET /api/rings`
| Field | Description |
|---|---|
| **Request** | None |
| **Response** | `{ "machine_name": { "1": {...}, ... }, ... }` |
| **Data Returned** | All rings_config data (every machine, every slot) |
| **Refresh Interval** | 5-second cache TTL |

#### `GET /api/rings/{machine}`
| Field | Description |
|---|---|
| **Request** | Machine name path param |
| **Response** | `{ "1": {...}, "2": {...}, ... }` |
| **Data Returned** | Rings data for one machine (slot-keyed dict) |
| **Refresh Interval** | No cache |

#### `GET /api/rings_config`
| Field | Description |
|---|---|
| **Request** | None |
| **Response** | Content of `rings_config.json` |
| **Data Returned** | Live ring slot configuration (serial, mac, state, firmware) |
| **Refresh Interval** | File served directly (no cache control) |

### 2.2 Slot Control Endpoints

#### `POST /api/machine/{machine}/slot/{slot}/charger/{action}`
| Field | Description |
|---|---|
| **Request** | Machine, slot (1-64), action (on/off) |
| **Response** | `{"ok": bool, "machine": ..., "slot": ..., "action": ..., "upstream": {...}}` |
| **Data Returned** | Status of charger command |
| **Refresh Interval** | On-demand — proxies to machine's internal API |

#### `GET /api/machine/{machine}/charger-status`
| Field | Description |
|---|---|
| **Request** | Machine path param |
| **Response** | `{"ok": true, "slots": {slot: {"state": "on"|"off", "source": "...", "charger_on": bool, "charging_current_ma": float}}}` |
| **Data Returned** | Charger state for every slot on the machine |
| **Refresh Interval** | On-demand |

#### `POST /api/machine/{machine}/slot/{slot}/awm/{action}`
| Field | Description |
|---|---|
| **Request** | Machine, slot (1-64), action (start/stop) |
| **Response** | `{"ok": bool, "machine": ..., "slot": ..., "action": ..., "message": "..."}` |
| **Data Returned** | AWM command status |
| **Refresh Interval** | On-demand — sends hex commands to machine |

### 2.3 Historical Archive Endpoints

#### `GET /api/old-data/search/{serial}`
| Field | Description |
|---|---|
| **Request** | Serial number path param |
| **Response** | `{"ok": true, "count": N, "results": [...], "index_source": "pg"|"ring_status"}` |
| **Data Returned** | Latest + historical records for a serial across all machines |
| **Refresh Interval** | On-demand, queries PostgreSQL |

#### `POST /api/old-data/search`
| Field | Description |
|---|---|
| **Request** | `{"serials": [...], "use_new_table": bool}` |
| **Response** | Same as GET version, but supports batch |
| **Data Returned** | Multi-serial search results |
| **Refresh Interval** | On-demand |

#### `POST /api/old-data/ingest-file`
| Field | Description |
|---|---|
| **Request** | `{"file_path": "..."}` |
| **Response** | `{"ok": true}` |
| **Data Returned** | Ingestion confirmation |
| **Refresh Interval** | Manual trigger |

### 2.4 Diagnostic Endpoints (all `POST` unless noted)

All under `/api/machine/{machine}/diagnose/`:

| Endpoint | HTTP | Data Returned |
|---|---|---|
| `connect` | POST | SSH connection check result |
| `scan` | POST | Button scan results |
| `location/{slot}` | GET | Slot location read |
| `led/{action}` | POST | LED control result |
| `full` | POST | Full diagnostics suite |
| `troubleshoot/{fix}` | POST | Fix execution result (reconfigure_mcps / kill_conflicts) |
| `motor` | GET | Motor status |
| `audit` | POST | Folder audit results |
| `audit/processes` | POST | Running processes audit |
| `audit/system` | POST | System audit |
| `mcp/scan` | POST | MCP I2C scan |
| `mcp/repair` | POST | MCP repair result |
| `mcp/advanced-repair` | POST | MCP advanced repair |
| `button/advanced-repair` | POST | Button advanced repair |
| `kill-conflicts` | POST | Process conflict resolution |
| `bt/status` | GET | Bluetooth adapter status |
| `bt/diagnose` | POST | Bluetooth diagnosis |
| `bt/scan` | POST | Bluetooth device scan |
| `bt/reset` | POST | Bluetooth reset |
| `bt/full-reset` | POST | Full Bluetooth reset |
| `bt/recover` | POST | Bluetooth recovery |
| `bt/connection-check` | POST | Connection integrity check |
| `bt/live-log` | POST | Live BT log capture |
| `bt/fix-crash-loop` | POST | BT crash loop fix |
| `bt/fix-pairing-popup` | POST | Safe pairing popup fix |
| `bt/fix-pairing-popup-persistent` | POST | Persistent pairing popup fix |
| `led/restore` | POST | LED state restore |
| `led/diagnose` | POST | LED diagnostics |
| `logs` | GET | Fetch app logs (param: lines=N) |

---

## SECTION 3 — Metrics Calculated

### 3.1 BDR (Battery Discharge Rate)

| Property | Value |
|---|---|
| **Formula** | `Δbattery_pct / Δtime` — derived from charge/discharge cycle readings. Stored as `avg_bdr` in device. If unavailable, computed as `mean(completed_cycles[].bdr)`. |
| **Source** | `slot.bdr_data.avg_bdr` (stored) OR computed from `slot.bdr_state.completed_cycles[].bdr` (estimated). |
| **Meaning** | Rate of battery discharge per cycle. Higher magnitude = faster drain. Units: % per unit time (mA equivalent in some readings). Negative values indicate discharge. |

### 3.2 Average BDR

| Property | Value |
|---|---|
| **Formula** | `stored_avg_bdr` (from device) if available; otherwise `sum(completed_cycles.bdr) / count(completed_cycles)` |
| **Source** | `_calc_avg_bdr()` in `api.py:887-901`. Priority: `bdr_data.avg_bdr` → computed from `completed_cycles[].bdr` |
| **Meaning** | Mean discharge rate across all completed cycles. Used as the primary health/quality metric. |

### 3.3 Stored Average BDR

| Property | Value |
|---|---|
| **Formula** | Direct read from `bdr_data.stored_avg_bdr` |
| **Source** | Device firmware output |
| **Meaning** | The firmware-computed average BDR at test finalization. The "ground truth" value. |

### 3.4 Inter-Cycle Average BDR

| Property | Value |
|---|---|
| **Formula** | Direct read from `bdr_data.inter_cycle_avg_bdr` |
| **Source** | Device firmware |
| **Meaning** | Average BDR computed between cycle transitions. May differ from stored avg. |

### 3.5 Battery Current

| Property | Value |
|---|---|
| **Formula** | Direct read from `slot.battery_current` (integer) or `charging_current_ma` (float) |
| **Source** | Device sensor reading |
| **Meaning** | Instantaneous battery current in mA. Positive = charging, negative = discharging. |

### 3.6 Cycle Count

| Property | Value |
|---|---|
| **Formula** | `max(len(bdr_state.completed_cycles), len(bdr_data.cycles))` or `bdr_data.final_cycle` |
| **Source** | Derived from completed cycle arrays or final_cycle field |
| **Meaning** | Number of charge/discharge cycles completed in the current or completed test. |

### 3.7 Completed Workouts

| Property | Value |
|---|---|
| **Formula** | Count of `start_pct` drops between consecutive cycles (indicates a full discharge → charge cycle). Two strategies: from `bdr_data.cycles` or from `completed_cycles` grouped by restart. See `_calc_completed_workouts()` in `api.py:957-963` |
| **Source** | Computed from cycle data |
| **Meaning** | Number of full workout cycles completed. A workout = a full discharge event detected by significant start_pct drop. |

### 3.8 Total Cycles / Completed Cycles

| Property | Value |
|---|---|
| **Formula** | `max(len(bdr_state.completed_cycles), len(bdr_data.cycles))` |
| **Source** | Derived from cycle arrays |
| **Meaning** | Total number of BDR cycles recorded. In the response payload, `completed_cycles` and `total_cycles` are reported as the same value. |

### 3.9 State Classification (Pass / Fail / BDR_RUNNING / ASSIGNED)

| Property | Value |
|---|---|
| **Formula** | Direct read from `slot.state` |
| **Source** | Device state machine |
| **Meaning** | **PASSED** = BDR test passed. **FAILED** = BDR test failed. **BDR_RUNNING** = test in progress. **ASSIGNED** (absence of the above) = ring assigned but no test started/completed. |

### 3.10 Battery Percentage (from `bdr_battery_history`)

| Property | Value |
|---|---|
| **Formula** | Each history entry: `[timestamp, battery_pct, bdr_value, phase_name, flag]` |
| **Source** | `slot.bdr_battery_history[][1]` (index 1 = battery %) |
| **Meaning** | Battery percentage at each measurement point over the test duration. Time-series data. |

### 3.11 BDR History Value (from `bdr_battery_history`)

| Property | Value |
|---|---|
| **Formula** | Each history entry index 2 = instantaneous BDR reading |
| **Source** | `slot.bdr_battery_history[][2]` |
| **Meaning** | Instantaneous discharge rate at each measurement point. |

### 3.12 Health (Heatmap Color Classification)

| Property | Value |
|---|---|
| **Formula** | Based on `avg_bdr` ranges mapped to health categories in the frontend heatmap |
| **Source** | Computed from avg_bdr in `app.js` |
| **Meaning** | Visual health indicator: green (good), yellow (warning), red (bad). Thresholds defined in frontend heatmap rendering. |

### 3.13 Machine Average BDR

| Property | Value |
|---|---|
| **Formula** | The avg_bdr value for a slot, aliased as `machine_avg_bdr` in response |
| **Source** | Same as avg_bdr |
| **Meaning** | Per-machine-per-slot average BDR, used for aggregation views. |

---

## SECTION 4 — Historical Data

### What Exists

| Source | Format | Size | Range |
|---|---|---|---|
| PostgreSQL `archive_entries` | Structured rows | Indeterminate | Spans dates visible in migration dumps (Jul 2026) |
| SQLite `archive.db` | SQLite DB | 11.4 GB | Chunk files dating from multiple backfill operations |
| JSON archive files (`DESTINATION/archive/`) | JSON files (machine/date/time.json) | ~3 day retention (auto-pruned) | Rolling 3-day window |
| Backfill chunks (`data/bf_chunks/`) | JSON arrays | 5 chunks (0-2000) | Extracted historical data |
| PostgreSQL dumps (`archive_entries_backup_*.dump`) | PostgreSQL dump | ~Jul 2026 | Standalone backup snapshots |

### Can AI Compare Time Periods?

| Comparison | Possible? | Explanation |
|---|---|---|
| **Today vs Yesterday** | YES | JSON archive files exist in `machine/date/` layout. Enough resolution if pruner hasn't removed yesterday's files. |
| **Today vs Last Week** | PARTIAL | Only if archive files for last week have not been pruned (pruner keeps 3 days by default). However, `archive_entries` in PostgreSQL may have data going further back. |
| **Today vs Last Month** | PARTIAL | Depends on whether `archive_entries` table has been populated via migration. The `ring_status` table only keeps 30 days. |
| **Today vs Last Year** | NO | No data spans a full year. The project has been running for months (backfill chunks exist) but not a full year. |
| **Same weekday comparison** | LIMITED | Enough data for some weekday-over-weekday comparisons if archive entries cover sufficient range. |

### Limitations

1. **PostgreSQL `archive_entries`** content depends on migration completeness. Not all SQLite data may have been migrated.
2. **JSON files** are pruned after 3 days by default. Only `archive_entries` and SQLite have long-term data.
3. **`ring_status`** is the latest-state only — no history. It is overwritten on every upsert.
4. **`live_bdr_raw` / `live_rings_raw`** contain only the most recent snapshot per machine — zero history.
5. **Backfill chunks** exist but are static extracts, not continuously updated.
6. **No retention policy** is documented for `archive_entries` — data may grow unbounded.

---

## SECTION 5 — Machine Data (Everything AI Knows About a Machine)

From `machines.json`:

```
name         → aqc-03, aqc-04, ... aqc-48 (42 machines)
ip           → 172.16.18.x (x = 27..80)
user         → same as machine name
removed_slots → [1, 23, 60] (only aqc-05 has these)
```

From `live_bdr_raw` (each machine's current BDR session):

| Field | Description |
|---|---|
| `machine_name` | Machine identifier |
| `content` | Full BDR session JSON |
| `_meta.downloaded_at` | Timestamp of last download |

From `live_rings_raw` (each machine's current ring config):

| Field | Description |
|---|---|
| `machine_name` | Machine identifier |
| `content` | Full rings_config JSON |
| `_meta.downloaded_at` | Timestamp of last download |

From `machine_logs`:

| Field | Description |
|---|---|
| `machine_name` | Machine identifier |
| `machine_ip` | IP address at collection time |
| `fetch_time` | When logs were fetched |
| `file_name` | Log file name |
| `file_size` | Log file size |
| `storage_location` | Where log is stored |
| `collection_status` | success / error |
| `error_message` | Error detail if failed |

From diagnostics (on-demand SSH):

| Capability | Description |
|---|---|
| SSH connectivity test | Connection success/fail + latency |
| Button scan | Detect button presses across all slots |
| Slot location | Physical slot location read |
| LED control | Test/restore LED per slot or all |
| Motor status | Motor state |
| MCP I2C scan | MCP expander I2C bus scan |
| MCP repair | Fix MCP issues |
| Folder audit | List of application folders |
| Process audit | Running processes |
| System audit | System info |
| Bluetooth status | BT adapter status |
| Bluetooth diagnosis | BT health check |
| Bluetooth scan | Discover BT devices |
| Bluetooth reset/repair | BT troubleshooting |
| App logs | Fetch app.log contents |
| Kill conflicts | Kill conflicting processes |
| Troubleshoot | Run fixes: reconfigure_mcps, kill_conflicts |

**What is NOT known about a machine:**
- CPU/RAM/disk utilization
- Network latency profile (only ping at connection time)
- Temperature or environmental data
- Historical uptime
- Number of slots physically populated vs empty

---

## SECTION 6 — Slot Data (Everything AI Knows About a Slot)

### From BDR Session (`/api/bdr`):

```
slot[N]:
  state                → "BDR_RUNNING" | "PASSED" | "FAILED"
  serial_number        → e.g. "RP-CH3-P18-WD-PG08-0000493"
  product              → "PRO" (from device)
  firmware_version     → e.g. "05.24.34.52"
  ring_mac             → Bluetooth MAC
  ring_name            → e.g. "UH_F6644DCB82B7"
  battery_current      → e.g. 84 (mA)
  charging_current_ma  → e.g. -1.288 (mA, negative = charging)
  dead_state           → null | "SUSPECTED" | "CONFIRMED"
  dead_confirm_passes  → integer count
  discharge_connect_failures → integer count
  error                → error message or null
  queued_at            → queue timestamp or null
  
  bdr_data (present when state is PASSED/FAILED):
    avg_bdr            → average discharge rate
    stored_avg_bdr     → firmware-computed average
    inter_cycle_avg_bdr → inter-cycle average
    phase_at_finalize  → phase at test end
    final_cycle        → final cycle number
    phase_start_time   → epoch of phase start
    cycles[].cycle     → cycle number
    cycles[].start_pct → start battery %
    cycles[].end_pct   → end battery %
    cycles[].duration_min → cycle duration in minutes
    cycles[].bdr       → BDR for this cycle
    cycles[].readings  → number of readings
    cycles[].warning   → warning flag
    death_count        → battery death count
  
  bdr_state (present when state is BDR_RUNNING):
    phase              → current phase name
    cycle              → current cycle number
    phase_start_time   → epoch
    last_charge_change_time → epoch
    completed_cycles[].cycle, start_pct, end_pct, duration_min, bdr, readings, warning
    
  bdr_battery_history:
    [timestamp, battery_pct, bdr_value, phase_name, flag]
    → Time series of battery % and BDR over entire test duration
```

### From Rings Config (`/api/rings` + `/api/rings_config`):

```
slot[N]:
  serial_number        → ring serial
  ring_mac             → Bluetooth MAC
  ring_name            → friendly name
  state                → same state (BDR_RUNNING/PASSED/FAILED)
  firmware_version     → firmware string
  hardware_version     → hardware version (often null)
  step_statuses        → { "BDR_TEST": "IN_PROGRESS" | ... }
  dead_state           → null/"SUSPECTED"/"CONFIRMED"
  dead_confirm_passes  → count
  discharge_connect_failures → count
  queued_at            → timestamp or null
  error                → error or null
```

### From `ring_status` (fast lookup):

```
serial_number, machine, slot, ring_mac, ring_name,
state, phase, cycle, avg_bdr, battery_current,
firmware_version, phase_start_time, last_charge_change_time,
saved_at, updated_at
```

### From Historical Archive (`/api/old-data/search/{serial}`):

```
row_type         → "latest" | "history"
serial_number    → ring serial
machine          → machine name
date             → YYYY-MM-DD
time             → HH:MM:SS (file stem)
slot             → slot number
state            → test state
battery_current  → mA reading
firmware_version → firmware string
ring_mac         → Bluetooth MAC
ring_name        → ring name
avg_bdr          → average BDR
machine_avg_bdr  → aliased avg_bdr
avg_bdr_is_stale → boolean
avg_bdr_is_estimated → boolean
stored_avg_bdr   → original stored value
inter_cycle_avg_bdr → inter-cycle value
test_start       → epoch
phase            → phase name
cycle            → cycle number
snapshots        → count (typically 1 per row)
total_cycles     → total cycles
completed_cycles → completed count
completed_workouts → workout count
start_time       → epoch (alias)
last_update      → saved_at timestamp
saved_at         → saved_at timestamp
file_path        → original JSON file path
```

---

## SECTION 7 — Battery Categories

Classification logic is implemented in `app.js:966-980` (`classifySerial()`).

### How Categories Are Identified

| Category | Identification Rule | Example Serial |
|---|---|---|
| **RT CONVERSION** | The third segment (parts[2]) contains code matching `IRR`, `IR3`, `IR4`, `CR3`, or `CR4`. | `RA-CH2-IR4-WB-RT09-0002386` |
| **WABI SABI** | The third segment contains code matching `IW1`, `IW2`, `IW3`, `CW3`, or `CW4`. | `RA-CH3-IW3-WB-WR10-0002036` |
| **LUX** | Serial length ≥ 15 AND character at index 14 (15th char) is `L`. | (15th char = L) |
| **PRO** | Serial starts with `RP` (first 2 characters). | `RP-CH3-P18-WD-PG08-0000493` |
| **AIR** | Default — any serial that doesn't match the above rules. | Catch-all |

### Serial Format Patterns

- **RT / Wabi Sabi format:** `RA-CH{2|3}-{IR3|IR4|IW3|...}-{WB|W1}-RT{N}-{serial#}`
- **PRO format:** `RP-{CH3}-{P18}-{WD}-{PG08}-{serial#}`
- **AIR format:** Everything else
- **LUX:** Identified by position (15th char = 'L'), not by prefix

### Notes

- SKU is extracted as `parts[4]` from the dashed serial number (or `--` if not available).
- Category counts and SKU breakdowns are computed on the frontend in `buildDataVizData()`.
- These categories are used for:
  - Color-coded slot badges (PRO = blue, LUX = gold)
  - Data Visualization view (pie charts per category)
  - Filtering/sorting in the dashboard

---

## SECTION 8 — AI Opportunities

### 8.1 BDR Value Analysis

| Dataset | BDR values per cycle per slot per machine |
|---|---|
| **Possible Insights** | Distribution of BDR values by category, firmware version, machine. Correlation between BDR and battery_current. |
| **Possible Trends** | BDR degradation over time per ring serial. BDR drift after firmware updates. |
| **Possible Recommendations** | Flag rings approaching unhealthy BDR thresholds. Recommend recalibration or replacement. |
| **Possible Anomaly Detection** | Sudden BDR spikes. BDR values outside 3-sigma per category. BDR values that don't match expected discharge curves. |

### 8.2 Pass/Fail Rate Analysis

| Dataset | Test outcomes (PASSED/FAILED) per slot per ring per machine |
|---|---|
| **Possible Insights** | Pass rate by machine, slot, firmware version, category, operator (implicit). |
| **Possible Trends** | Pass rate degradation over time. Slot-specific failure patterns. |
| **Possible Recommendations** | Identify problematic machines or slots. Schedule maintenance. |
| **Possible Anomaly Detection** | Unexpected clusters of failures on specific slots or machines. |

### 8.3 Battery Discharge Profile Analysis

| Dataset | `bdr_battery_history` — time series of battery % |
|---|---|
| **Possible Insights** | Discharge curve shapes by category. Normal vs abnormal discharge profiles. |
| **Possible Trends** | Profile changes across firmware versions. Capacity fade over cycles. |
| **Possible Recommendations** | Flag abnormal discharge curves. Predict remaining battery life. |
| **Possible Anomaly Detection** | Voltage sags, premature cutoffs, erratic discharge patterns. |

### 8.4 Cycle Pattern Analysis

| Dataset | Cycle timestamps, durations, start/end percentages |
|---|---|
| **Possible Insights** | Typical cycle duration by category and phase. Charge/discharge symmetry. |
| **Possible Trends** | Duration lengthening (indicating battery degradation). |
| **Possible Recommendations** | Set expected duration windows per battery type. |
| **Possible Anomaly Detection** | Abnormally short or long cycles. Cycles with unexpected restarts. |

### 8.5 Slot Utilization Analysis

| Dataset | Slot occupancy, slot assignments over time |
|---|---|
| **Possible Insights** | Which slots are most/least used. Utilization by machine. |
| **Possible Trends** | Seasonal or shift-based utilization patterns. |
| **Possible Recommendations** | Balance load across machines. Identify underutilized capacity. |
| **Possible Anomaly Detection** | Slots with abnormal vacancy rates. |

### 8.6 Firmware Version Analysis

| Dataset | Firmware version per ring, per machine, over time |
|---|---|
| **Possible Insights** | Which firmware versions produce best pass rates / best BDR values. |
| **Possible Trends** | Improvement or regression after firmware changes. |
| **Possible Recommendations** | Recommend rolling out best-performing firmware versions. |
| **Possible Anomaly Detection** | Rings with outdated or mismatched firmware. |

### 8.7 Discharge Connect Failure Analysis

| Dataset | `discharge_connect_failures` counts per slot/ring |
|---|---|
| **Possible Insights** | Failure patterns by slot, machine, ring category. |
| **Possible Trends** | Increasing failure rates indicating hardware wear. |
| **Possible Recommendations** | Preemptively service slots with rising failure counts. |
| **Possible Anomaly Detection** | Sudden spikes in failure count. Rings with abnormally high failures. |

### 8.8 Dead Battery Detection

| Dataset | `dead_state` (SUSPECTED/CONFIRMED), `dead_confirm_passes`, `death_count` |
|---|---|
| **Possible Insights** | Correlation between dead state and BDR values, cycle counts, firmware. |
| **Possible Trends** | Which batteries are more likely to die at which cycle counts. |
| **Possible Recommendations** | Preemptive removal of rings with high death probability. |
| **Possible Anomaly Detection** | Batteries with unexpected death_state transitions. |

### 8.9 Machine Performance Comparison

| Dataset | All metrics grouped by machine |
|---|---|
| **Possible Insights** | Which machines perform best/worst. Machine-specific bias. |
| **Possible Trends** | Machine performance degradation over time. |
| **Possible Recommendations** | Flag machines needing recalibration or maintenance. |
| **Possible Anomaly Detection** | Machine out of family with its peers. |

### 8.10 Category-Based Quality Analysis

| Dataset | All metrics grouped by battery category (AIR/PRO/LUX/RT/WABI SABI) |
|---|---|
| **Possible Insights** | Which categories have best pass rates, BDR values, longevity. |
| **Possible Trends** | Inter-category comparison over time. |
| **Possible Recommendations** | Focus quality efforts on lower-performing categories. |
| **Possible Anomaly Detection** | Out-of-family performance within a category. |

### 8.11 Historical Search & Recovery

| Dataset | `archive_entries` — historical snapshots by serial |
|---|---|
| **Possible Insights** | Full lifecycle of a ring across machines. Historical quality changes. |
| **Possible Trends** | Ring performance trajectory over its lifetime. |
| **Possible Recommendations** | Predict end-of-life for rings. |
| **Possible Anomaly Detection** | Rings with wildly varying BDR across different machines. |

### 8.12 Time-Based Pattern Detection

| Dataset | saved_at timestamps across all tables |
|---|---|
| **Possible Insights** | Peak testing hours, day-of-week patterns, weekend vs weekday behavior. |
| **Possible Trends** | Production volume changes over time. |
| **Possible Recommendations** | Staffing and capacity planning. |
| **Possible Anomaly Detection** | Unexpected drops or spikes in testing activity. |

---

## SECTION 9 — AI Limitations

### Data That Is Missing

| Missing Data | Impact on AI |
|---|---|
| **Environmental data** (temperature, humidity) | Cannot correlate BDR values with environmental conditions. Temperature affects battery discharge rates significantly. |
| **Operator identity** | Cannot analyze operator-specific quality patterns. |
| **Production lot / batch information** | Cannot trace quality issues to manufacturing batches. |
| **Ring age / manufacturing date** | Cannot calculate age-based degradation curves. |
| **Machine hardware specs** (CPU, RAM, disk) | Cannot diagnose machine performance issues. |
| **Network latency / reliability metrics** | Cannot correlate data freshness issues with network health. |
| **Calibration records** | Cannot verify machine calibration status. |
| **Maintenance logs** | Cannot correlate maintenance events with quality changes. |
| **Component-level data** (charger board, MCP) | Cannot diagnose root causes of hardware failures. |
| **Test fixture IDs** | Cannot track fixture-level effects. |
| **Software versions** (beyond firmware) | Cannot correlate OS-level changes with test quality. |
| **Historical machine availability** | Cannot calculate uptime or reliability metrics. |
| **External factors** (power events, network outages) | Cannot explain data gaps or anomalies. |

### Questions That Cannot Be Answered

1. **Why did this ring fail?** — Insufficient diagnostic data at failure time. Only final state and BDR value are available.
2. **Is this machine calibrated?** — No calibration records exist.
3. **Who tested this ring?** — No operator tracking.
4. **Was the temperature normal during this test?** — No environmental data.
5. **Is this degradation expected for a battery of this age?** — No manufacturing date.
6. **How many tests has this machine done in its lifetime?** — Machine_logs may have partial data but no reliable counters.
7. **What changed between last week and this week?** — If archive was pruned, data is lost.
8. **Which batch of rings has quality issues?** — No batch/lot tracking.
9. **What is the optimal test duration?** — Test duration is implicit but not explicitly labeled.
10. **Are certain charger settings better for certain batteries?** — Charger state is binary (on/off), no granular setting.

### Reports That Are Impossible

| Report | Reason Impossible |
|---|---|
| **Year-over-Year Quality Trend** | Less than 1 year of data exists |
| **Mean Time Between Failures (MTBF)** | No failure time tracking beyond latest state |
| **Predictive Calendar-Based Maintenance Schedule** | No equipment age or usage counters |
| **Environmental Impact on BDR** | No environmental data collected |
| **Operator Efficiency Comparison** | No operator identity tracked |
| **Cost of Quality by Batch** | No batch/lot data |
| **Supply Chain Quality Correlation** | No supply chain data integrated |
| **Real-Time Anomaly Detection with Root Cause** | Insufficient diagnostic breadth for root cause |

---

## SECTION 10 — Final Readiness Assessment

### Ratings (1-10)

| Dimension | Rating | Explanation |
|---|---|---|
| **Data Quality** | 6/10 | BDR values are present and structured consistently. However: stale values are sometimes replaced with fallbacks, avg_bdr is sometimes estimated vs stored, and the distinction is not always reliable. Null/zero BDR values cause fallback logic that obscures true quality. |
| **Historical Coverage** | 5/10 | PostgreSQL has some historical data via `archive_entries` and `ring_status` (30-day retention). JSON archive files are limited to 3 days. SQLite has 11.4 GB of raw data but migration to PG may be incomplete. No data spans a full year. Backfill exists but is not continuously maintained. |
| **Analytics Readiness** | 7/10 | Core metrics (BDR, pass/fail, cycles, workouts) are well-defined and computable. Category classification is clear. Time series data exists for battery history. The API provides structured access. Missing: aggregated views, pre-computed KPIs, statistical summaries. |
| **AI Readiness** | 5/10 | The data model is simple and well-understood, making it feasible for basic ML (pass/fail classification, BDR prediction, anomaly detection). However: historical data gaps, missing environmental context, no operator tracking, and limited retention policies significantly constrain what an AI can learn and infer. |

### Verdict

**The project is partially ready for AI integration without architecture changes.**

**What an AI can do today:**
- Classify pass/fail patterns by machine, slot, firmware, category
- Detect anomalous BDR values (outliers, trends)
- Predict pass/fail likelihood based on early-cycle data
- Identify slot-specific or machine-specific bias
- Analyze discharge curve shapes
- Compute category-level quality metrics
- Flag rings with degradation over time (within data window)

**What requires architecture changes:**
- Long-term trend analysis (needs data retention beyond 30 days)
- Root cause diagnosis (needs environmental, operator, and calibration data)
- Predictive maintenance (needs usage counters, age data)
- Full lifecycle tracking (needs manufacturing date, batch info)

**Recommendation for immediate AI integration:**
1. Focus on **classification** (will this ring pass/fail?) and **anomaly detection** (is this BDR abnormal?) — these work with current data.
2. Extend `archive_entries` retention to at least 6 months before attempting trend prediction.
3. Add environmental sensors or integrate external temperature data for BDR normalization.
4. The `ring_status` table is a good real-time feature store for AI inference.
5. Stream metrics to an ML pipeline via the existing API — no schema changes needed.
