import json
import mmap
import os
import re
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from diagnostics import (
    check_connection,
    button_scan,
    read_location,
    led_control,
    full_diagnostics,
    troubleshoot,
    motor_status,
    mcp_scan,
    mcp_repair,
    mcp_advanced_repair,
    button_advanced_repair,
    audit_folders,
    audit_processes,
    audit_system,
    kill_conflicts,
    bt_status,
    bt_diagnose,
    bt_scan,
    bt_reset,
    bt_full_reset,
    bt_recover,
    bt_connection_check,
    bt_live_log,
    bt_fix_crash_loop,
    bt_fix_pairing_popup_safe,
    bt_fix_pairing_popup_persistent,
    fetch_app_logs,
)

from postgres_db import (
    is_available as pg_available,
    init_db as init_pg,
    get_live_bdr,
    get_live_bdr_machine,
    get_live_rings,
    get_live_rings_machine,
    sync_machines_from_files,
    list_machines_pg,
    get_connection,
    get_live_bdr_fallback,
    get_live_bdr_machine_fallback,
    get_live_rings_fallback,
    get_live_rings_machine_fallback,
    list_machines_fallback,
)


# SQLite database for archive entries
_archive_db_path = os.path.join(os.path.dirname(__file__), "archive.db")
_archive_db_lock = threading.Lock()

def _init_archive_db():
    """Initialize SQLite database for archive entries."""
    with _archive_db_lock:
        conn = sqlite3.connect(_archive_db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-8000")
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS archive_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_number TEXT NOT NULL,
                serial_lower TEXT NOT NULL,
                file_path TEXT NOT NULL,
                machine TEXT,
                state TEXT,
                machine_avg_bdr REAL,
                bdr REAL,
                snapshots INTEGER,
                total_cycles INTEGER,
                completed_cycles INTEGER,
                start_time REAL,
                last_update REAL,
                saved_at TEXT,
                created_at REAL DEFAULT (strftime('%s', 'now')),
                UNIQUE(serial_number, file_path)
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_serial_number ON archive_entries(serial_number)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_path ON archive_entries(file_path)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON archive_entries(created_at)
        """)
        # Add saved_at column if it doesn't exist (schema migration)
        try:
            c.execute("ALTER TABLE archive_entries ADD COLUMN saved_at TEXT")
        except sqlite3.OperationalError:
            pass  # column already exists
        # Add slot column if it doesn't exist (schema migration)
        try:
            c.execute("ALTER TABLE archive_entries ADD COLUMN slot INTEGER")
        except sqlite3.OperationalError:
            pass  # column already exists
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_saved_at ON archive_entries(saved_at)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_machine ON archive_entries(machine)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_serial_lower ON archive_entries(serial_lower)
        """)
        # Schema migrations for additional columns
        for col_def in [
            ("firmware_version", "TEXT"),
            ("ring_mac", "TEXT"),
            ("ring_name", "TEXT"),
            ("stored_avg_bdr", "REAL"),
            ("inter_cycle_avg_bdr", "REAL"),
            ("phase", "TEXT"),
            ("cycle", "INTEGER"),
            ("completed_workouts", "INTEGER"),
            ("avg_bdr_is_estimated", "INTEGER"),
        ]:
            try:
                c.execute(f"ALTER TABLE archive_entries ADD COLUMN {col_def[0]} {col_def[1]}")
            except sqlite3.OperationalError:
                pass
        # Migrate old entries: copy last_update into saved_at if saved_at is null
        try:
            c.execute("UPDATE archive_entries SET saved_at = last_update WHERE saved_at IS NULL AND last_update IS NOT NULL")
        except Exception:
            pass
        # Remove old garbage entries written by broken _add_archive_entry (all NULL data fields)
        c.execute("DELETE FROM archive_entries WHERE last_update IS NULL AND saved_at IS NULL")
        # Migration: add serial_lower column if missing
        try:
            c.execute("ALTER TABLE archive_entries ADD COLUMN serial_lower TEXT")
            c.execute("UPDATE archive_entries SET serial_lower = LOWER(serial_number) WHERE serial_lower IS NULL")
            print("[api] Populated serial_lower column")
        except sqlite3.OperationalError:
            pass  # column already exists
        c.execute("CREATE INDEX IF NOT EXISTS idx_serial_lower ON archive_entries(serial_lower)")
        # Migration: fix incorrect file_path UNIQUE -> UNIQUE(serial_number, file_path)
        try:
            c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='archive_entries'")
            row = c.fetchone()
            if row and 'file_path TEXT NOT NULL UNIQUE' in row[0]:
                print("[api] Migrating archive_entries schema: file_path UNIQUE -> UNIQUE(serial_number, file_path)")
                c.execute("""
                    CREATE TABLE archive_entries_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        serial_number TEXT NOT NULL,
                        serial_lower TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        machine TEXT,
                        state TEXT,
                        machine_avg_bdr REAL,
                        bdr REAL,
                        snapshots INTEGER,
                        total_cycles INTEGER,
                        completed_cycles INTEGER,
                        start_time REAL,
                        last_update REAL,
                        saved_at TEXT,
                        created_at REAL DEFAULT (strftime('%s', 'now')),
                        slot INTEGER,
                        firmware_version TEXT,
                        ring_mac TEXT,
                        ring_name TEXT,
                        stored_avg_bdr REAL,
                        inter_cycle_avg_bdr REAL,
                        phase TEXT,
                        cycle INTEGER,
                        completed_workouts INTEGER,
                        UNIQUE(serial_number, file_path)
                    )
                """)
                c.execute("INSERT OR IGNORE INTO archive_entries_new (id, serial_number, serial_lower, file_path, machine, state, machine_avg_bdr, bdr, snapshots, total_cycles, completed_cycles, start_time, last_update, saved_at, created_at, slot, firmware_version, ring_mac, ring_name, stored_avg_bdr, inter_cycle_avg_bdr, phase, cycle, completed_workouts) SELECT id, serial_number, lower(serial_number), file_path, machine, state, machine_avg_bdr, bdr, snapshots, total_cycles, completed_cycles, start_time, last_update, saved_at, created_at, slot, firmware_version, ring_mac, ring_name, stored_avg_bdr, inter_cycle_avg_bdr, phase, cycle, completed_workouts FROM archive_entries")
                c.execute("INSERT OR IGNORE INTO archive_entries_new SELECT * FROM archive_entries")
                c.execute("DROP TABLE archive_entries")
                c.execute("ALTER TABLE archive_entries_new RENAME TO archive_entries")
                c.execute("CREATE INDEX IF NOT EXISTS idx_serial_number ON archive_entries(serial_number)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_file_path ON archive_entries(file_path)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON archive_entries(created_at)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_saved_at ON archive_entries(saved_at)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_machine ON archive_entries(machine)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_serial_lower ON archive_entries(serial_lower)")
                print("[api] Archive entries schema migration complete")
        except Exception:
            pass
        conn.commit()
        conn.close()

def _add_archive_entry(entry, file_path):
    """Add or update an archive entry in SQLite database."""
    with _archive_db_lock:
        conn = sqlite3.connect(_archive_db_path)
        c = conn.cursor()
        
        serial = entry.get("serial_number", "")
        c.execute("""
            INSERT OR REPLACE INTO archive_entries 
            (serial_number, serial_lower, file_path, machine, state, machine_avg_bdr, 
             bdr, firmware_version, ring_mac, ring_name, stored_avg_bdr,
             inter_cycle_avg_bdr, phase, cycle, completed_workouts,
             snapshots, total_cycles, completed_cycles, start_time, last_update, saved_at, slot,
             avg_bdr_is_estimated)
            VALUES (?, lower(?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            serial,
            serial,
            file_path,
            entry.get("machine"),
            entry.get("state"),
            entry.get("avg_bdr"),
            entry.get("battery_current"),
            entry.get("firmware_version"),
            entry.get("ring_mac"),
            entry.get("ring_name"),
            entry.get("stored_avg_bdr"),
            entry.get("inter_cycle_avg_bdr"),
            entry.get("phase"),
            entry.get("cycle"),
            entry.get("completed_workouts"),
            1,
            entry.get("total_cycles"),
            entry.get("completed_cycles"),
            entry.get("test_start"),
            entry.get("saved_at"),
            entry.get("saved_at"),
            entry.get("slot"),
            entry.get("avg_bdr_is_estimated", False),
        ))
        
        conn.commit()
        conn.close()

def _search_archive_db(serials):
    """Search archive database for given serial numbers."""
    conn = sqlite3.connect(_archive_db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    results = []
    for serial in serials:
        # Exact match first
        c.execute("SELECT * FROM archive_entries WHERE serial_number = ? ORDER BY saved_at DESC, last_update DESC", (serial,))
        rows = c.fetchall()
        for row in rows:
            results.append(dict(row))
        
        # Partial match
        if not rows:
            c.execute("SELECT * FROM archive_entries WHERE serial_number LIKE ? ORDER BY saved_at DESC, last_update DESC", (f"%{serial}%",))
            rows = c.fetchall()
            for row in rows:
                results.append(dict(row))
    
    conn.close()
    return results

def _prune_old_archive_files(days=7):
    """Prune JSON archive files older than N days, keeping the entries in SQLite."""
    cutoff = datetime.now() - timedelta(days=days)
    cutoff_epoch = cutoff.timestamp()
    
    pruned_count = 0
    archive_dir = Path(os.path.join(os.path.dirname(__file__), "..", "DESTINATION", "archive"))
    if not archive_dir.exists():
        return pruned_count
    
    for machine_dir in archive_dir.iterdir():
        if not machine_dir.is_dir():
            continue
        for date_dir in machine_dir.iterdir():
            if not date_dir.is_dir():
                continue
            for json_file in date_dir.glob("*.json"):
                file_mtime = json_file.stat().st_mtime
                if file_mtime < cutoff_epoch:
                    try:
                        json_file.unlink()
                        pruned_count += 1
                    except Exception as e:
                        print(f"Failed to prune {json_file}: {e}")
    
    return pruned_count


class CompactJSONResponse(JSONResponse):
    def render(self, content):
        return json.dumps(
            content,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")


app = FastAPI(title="AQC Machine Data API", version="1.0.0")

FILE_SYNC_INTERVAL = 30

_sync_thread_running = True
_last_successful_sync = None

_CACHE_TTL = 5  # seconds
_cache_lock = threading.Lock()
_bdr_cache = None
_bdr_cache_ts = 0.0
_rings_cache = None
_rings_cache_ts = 0.0


def _background_file_sync():
    """Check JSON files for changes and import directly to PostgreSQL."""
    global _last_successful_sync
    while _sync_thread_running:
        try:
            sync_machines_from_files()
            _last_successful_sync = time.time()
        except Exception as e:
            print(f"File sync error: {e}")
        time.sleep(FILE_SYNC_INTERVAL)


def validate_data_freshness():
    """Ensure data is not older than 5 minutes."""
    if not pg_available():
        return
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT machine_name, downloaded_at 
                    FROM live_bdr_raw 
                    WHERE downloaded_at < NOW() - INTERVAL '30 minutes'
                """)
                old_bdr = cur.fetchall()
                
                cur.execute("""
                    SELECT machine_name, downloaded_at 
                    FROM live_rings_raw 
                    WHERE downloaded_at < NOW() - INTERVAL '30 minutes'
                """)
                old_rings = cur.fetchall()
                
                if old_bdr or old_rings:
                    print(f"[api] WARNING: Stale data detected - BDR: {len(old_bdr)}, Rings: {len(old_rings)}")
                    force_resync_stale_data(old_bdr, old_rings)
                    
        finally:
            conn.close()
    except Exception as e:
        print(f"[api] Error validating data freshness: {e}")


def force_resync_stale_data(old_bdr, old_rings):
    """Force resync of stale data."""
    if not pg_available():
        return
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            for machine in old_bdr:
                cur.execute("DELETE FROM live_bdr_raw WHERE machine_name = %s", (machine[0],))
            for machine in old_rings:
                cur.execute("DELETE FROM live_rings_raw WHERE machine_name = %s", (machine[0],))
        conn.commit()
        sync_machines_from_files()
        print("[api] Stale data cleared and resync triggered")
    except Exception as e:
        print(f"[api] Error forcing resync: {e}")
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass








@app.on_event("startup")
def startup_event():
    _init_archive_db()
    print("Initializing PostgreSQL...")
    for attempt in range(3):
        if pg_available():
            try:
                init_pg()
                print("PostgreSQL initialized.")
                break
            except Exception as e:
                print(f"PostgreSQL init attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    print("PostgreSQL not available - data will not be served.")
                else:
                    time.sleep(2)
        else:
            if attempt == 2:
                print("PostgreSQL not available - data will not be served.")
            else:
                print(f"PostgreSQL not yet available, retrying in 2s (attempt {attempt+1}/3)...")
                time.sleep(2)
    thread = threading.Thread(target=_background_file_sync, daemon=True)
    thread.start()
    print(f"Background file sync started (every {FILE_SYNC_INTERVAL}s).")
    if not os.environ.get("NO_STARTUP_INDEX"):
        _ensure_archive_index()
        print("[api] Archive index building in background...")
    else:
        print("[api] Skipping startup index build (NO_STARTUP_INDEX set).")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


def load_machine_ip(machine: str) -> str:
    machines_json_path = Path(__file__).resolve().parent.parent / "machines.json"
    if not machines_json_path.exists():
        raise HTTPException(status_code=500, detail="machines.json not found")

    with machines_json_path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    def normalize_name(value: str) -> str:
        return value.strip().lower().replace("_", "-").replace(" ", "-")

    requested = normalize_name(machine)
    for item in config.get("machines", []):
        name = normalize_name(str(item.get("name", "")))
        if name == requested:
            ip = str(item.get("ip", "")).strip()
            if not ip:
                raise HTTPException(status_code=500, detail=f"No IP configured for {machine}")
            return ip

    raise HTTPException(status_code=404, detail=f"Machine {machine} not found")




# ── AWM hex constants ──────────────────────────────────────────────
AWM_START_CMD1 = "1001"
AWM_START_CMD2 = "90010103040104050101080203E80A0101"
AWM_STOP_CMD = "91"


def _send_awm_command(ip, slot, cmd_hex):
    """Send a single AWM hex command to a machine slot."""
    target = f"http://{ip}:8001/api/slot/{slot}/command"
    data = json.dumps({"cmd_hex": cmd_hex}).encode()
    req = urllib.request.Request(
        target, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status == 200, body


def _poll_awm_slot_ready(ip, slot, timeout=120):
    """Poll slot status until idle/ready or timeout. Returns True if ready."""
    status_url = f"http://{ip}:8001/api/slot/{slot}/status"
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(status_url)
            with urllib.request.urlopen(req, timeout=3) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                data = json.loads(body) if body else {}
                status = str(data.get("status", data.get("state", data.get("running", "")))).lower()
                if status in ("idle", "ready", "stop", "stopped", "false", "0", ""):
                    return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return True
        except Exception:
            pass
        time.sleep(1.0)
    return False


@app.post("/api/machine/{machine}/slot/{slot}/awm/{action}")
def slot_awm_action(machine: str, slot: int, action: str):
    action = action.strip().lower()
    if action not in {"start", "stop"}:
        raise HTTPException(status_code=400, detail="Action must be start or stop")
    if slot < 1 or slot > 64:
        raise HTTPException(status_code=400, detail="Slot must be between 1 and 64")

    ip = load_machine_ip(machine)

    if action == "start":
        try:
            ok, body = _send_awm_command(ip, slot, AWM_START_CMD1)
            if not ok:
                raise HTTPException(status_code=502, detail=f"Start cmd1 failed: {body}")
        except urllib.error.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Start cmd1 HTTP {e.code}: {e.read().decode()}")
        except urllib.error.URLError as e:
            raise HTTPException(status_code=502, detail=f"Start cmd1 unreachable: {e.reason}")

        _poll_awm_slot_ready(ip, slot)

        try:
            ok, body = _send_awm_command(ip, slot, AWM_START_CMD2)
            if not ok:
                raise HTTPException(status_code=502, detail=f"Start cmd2 failed: {body}")
        except urllib.error.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Start cmd2 HTTP {e.code}: {e.read().decode()}")
        except urllib.error.URLError as e:
            raise HTTPException(status_code=502, detail=f"Start cmd2 unreachable: {e.reason}")

        _poll_awm_slot_ready(ip, slot)

        return CompactJSONResponse(content={
            "ok": True, "machine": machine, "slot": slot, "action": "start",
            "message": f"AWM Start complete on slot {slot}",
        })

    else:  # stop
        try:
            ok, body = _send_awm_command(ip, slot, AWM_STOP_CMD)
            if not ok:
                raise HTTPException(status_code=502, detail=f"Stop cmd failed: {body}")
        except urllib.error.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Stop cmd HTTP {e.code}: {e.read().decode()}")
        except urllib.error.URLError as e:
            raise HTTPException(status_code=502, detail=f"Stop cmd unreachable: {e.reason}")

        _poll_awm_slot_ready(ip, slot)

        return CompactJSONResponse(content={
            "ok": True, "machine": machine, "slot": slot, "action": "stop",
            "message": f"AWM Stop complete on slot {slot}",
        })


@app.post("/api/machine/{machine}/slot/{slot}/charger/{action}")
def set_slot_charger(machine: str, slot: int, action: str):
    action = action.strip().lower()
    if action not in {"on", "off"}:
        raise HTTPException(status_code=400, detail="Action must be on or off")
    if slot < 1 or slot > 64:
        raise HTTPException(status_code=400, detail="Slot must be between 1 and 64")

    ip = load_machine_ip(machine)
    target = f"http://{ip}:8001/api/slot/{slot}/charger/{action}"
    req = urllib.request.Request(target, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                upstream = json.loads(body) if body else {}
            except json.JSONDecodeError:
                upstream = {"raw": body}
            return CompactJSONResponse(
                content={
                    "ok": True,
                    "machine": machine,
                    "slot": slot,
                    "action": action,
                    "target": target,
                    "upstream_status": resp.status,
                    "upstream": upstream,
                }
            )
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=502,
            detail=f"Machine charger API returned {e.code}: {detail}",
        )
    except urllib.error.URLError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach {machine} charger API at {target}: {e.reason}",
        )
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Timed out reaching {machine} charger API at {target}",
        )


@app.get("/api/machine/{machine}/charger-status")
def get_machine_charger_status(machine: str):
    ip = load_machine_ip(machine)
    target = f"http://{ip}:8001/api/status"
    req = urllib.request.Request(target, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=502,
            detail=f"Machine status API returned {e.code}: {detail}",
        )
    except urllib.error.URLError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach {machine} status API at {target}: {e.reason}",
        )
    except (TimeoutError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=504,
            detail=f"Could not read {machine} status API at {target}: {e}",
        )

    raw_slots = data.get("physical_slots") or {}
    slots = {}
    for slot_key, slot_data in raw_slots.items():
        if not isinstance(slot_data, dict):
            continue
        charger_on = slot_data.get("charger_on")
        current_ma = slot_data.get("charging_current_ma")
        if charger_on is None:
            state = "unknown"
            source = "current_only"
        else:
            state = "on" if bool(charger_on) else "off"
            source = "charger_on"
        slots[str(slot_key)] = {
            "state": state,
            "source": source,
            "charger_on": charger_on,
            "charging_current_ma": current_ma,
        }

    return CompactJSONResponse(
        content={
            "ok": True,
            "machine": machine,
            "target": target,
            "slots": slots,
        }
    )


@app.get("/api/health")
def health_check():
    global _last_successful_sync
    now = time.time()
    data_stale = False
    if _last_successful_sync is None:
        data_stale = True
    elif (now - _last_successful_sync) > 300:  # 5 minutes
        data_stale = True
        
    return CompactJSONResponse(content={
        "status": "healthy" if not data_stale else "degraded",
        "last_successful_sync": _last_successful_sync,
        "postgres_available": pg_available()
    })

@app.get("/api/machines")
def list_machines():
    machines_json_path = Path(__file__).resolve().parent.parent / "machines.json"

    db_machines = set()
    if pg_available():
        db_machines = set(list_machines_pg())

    config_machines = set()
    if machines_json_path.exists():
        with machines_json_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
            config_machines = {m["name"] for m in config.get("machines", [])}

    file_machines = set(list_machines_fallback())

    all_machines = sorted(db_machines | config_machines | file_machines)
    return CompactJSONResponse(content={"machines": all_machines})


@app.get("/api/bdr")
def get_all_bdr():
    global _bdr_cache, _bdr_cache_ts
    now = time.time()
    with _cache_lock:
        if _bdr_cache is not None and (now - _bdr_cache_ts) < _CACHE_TTL:
            return CompactJSONResponse(content=_bdr_cache)
    try:
        result = None
        if pg_available():
            try:
                result = get_live_bdr()
            except Exception as e:
                print(f"[API] DB query failed in get_all_bdr, falling back to files: {e}")
        if not result:
            result = get_live_bdr_fallback()
        if not result:
            result = {}
        with _cache_lock:
            _bdr_cache = result
            _bdr_cache_ts = time.time()
        return CompactJSONResponse(content=result)
    except Exception as e:
        print(f"[API] Error in get_all_bdr: {e}")
        import traceback
        traceback.print_exc()
        return CompactJSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/bdr/{machine}")
def get_bdr_machine(machine: str):
    try:
        if pg_available():
            try:
                content = get_live_bdr_machine(machine)
                if content is not None:
                    return CompactJSONResponse(content=content)
            except Exception as e:
                print(f"[API] DB query failed in get_bdr_machine({machine}), falling back to files: {e}")
        fallback = get_live_bdr_machine_fallback(machine)
        if fallback is not None:
            return CompactJSONResponse(content=fallback)
        return CompactJSONResponse(content={"error": "Machine not found"}, status_code=404)
    except Exception as e:
        print(f"[API] Error in get_bdr_machine({machine}): {e}")
        import traceback
        traceback.print_exc()
        return CompactJSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/rings")
def get_all_rings():
    global _rings_cache, _rings_cache_ts
    now = time.time()
    with _cache_lock:
        if _rings_cache is not None and (now - _rings_cache_ts) < _CACHE_TTL:
            return CompactJSONResponse(content=_rings_cache)
    try:
        result = None
        if pg_available():
            try:
                result = get_live_rings()
            except Exception as e:
                print(f"[API] DB query failed in get_all_rings, falling back to files: {e}")
        if not result:
            result = get_live_rings_fallback()
        if not result:
            result = {}
        with _cache_lock:
            _rings_cache = result
            _rings_cache_ts = time.time()
        return CompactJSONResponse(content=result)
    except Exception as e:
        print(f"[API] Error in get_all_rings: {e}")
        import traceback
        traceback.print_exc()
        return CompactJSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/rings/{machine}")
def get_rings_machine(machine: str):
    try:
        if pg_available():
            try:
                content = get_live_rings_machine(machine)
                if content is not None:
                    return CompactJSONResponse(content=content)
            except Exception as e:
                print(f"[API] DB query failed in get_rings_machine({machine}), falling back to files: {e}")
        fallback = get_live_rings_machine_fallback(machine)
        if fallback is not None:
            return CompactJSONResponse(content=fallback)
        return CompactJSONResponse(content={"error": "Machine not found"}, status_code=404)
    except Exception as e:
        print(f"[API] Error in get_rings_machine({machine}): {e}")
        import traceback
        traceback.print_exc()
        return CompactJSONResponse(content={"error": str(e)}, status_code=500)


# ── Diagnostic Endpoints ──────────────────────────────────────────
import typing as _t

@app.post("/api/machine/{machine}/diagnose/connect")
def diagnose_connect(machine: str):
    result = check_connection(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Connection failed")}, status_code=502)
    return CompactJSONResponse(content=result)

@app.post("/api/machine/{machine}/diagnose/scan")
def diagnose_scan(machine: str):
    result = button_scan(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Scan failed")}, status_code=502)
    return CompactJSONResponse(content=result)

@app.get("/api/machine/{machine}/diagnose/location/{slot}")
def diagnose_location(machine: str, slot: int):
    if slot < 1 or slot > 64:
        return CompactJSONResponse(content={"ok": False, "error": "Slot must be 1-64"}, status_code=400)
    result = read_location(machine, slot)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Read failed")}, status_code=502)
    return CompactJSONResponse(content=result)

@app.post("/api/machine/{machine}/diagnose/led/{action}")
def diagnose_led(machine: str, action: str, slot: _t.Optional[int] = None, color: _t.Optional[str] = None, r: _t.Optional[int] = None, g: _t.Optional[int] = None, b: _t.Optional[int] = None, delay: _t.Optional[float] = None):
    kwargs = {}
    if slot is not None:
        kwargs["slot"] = slot
    if color is not None:
        kwargs["color"] = color
    if r is not None:
        kwargs["r"] = r
    if g is not None:
        kwargs["g"] = g
    if b is not None:
        kwargs["b"] = b
    if delay is not None:
        kwargs["delay"] = delay
    result = led_control(machine, action, **kwargs)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "LED control failed")}, status_code=502)
    return CompactJSONResponse(content=result)

@app.post("/api/machine/{machine}/diagnose/full")
def diagnose_full(machine: str):
    result = full_diagnostics(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Diagnostics failed")}, status_code=502)
    return CompactJSONResponse(content=result)

@app.post("/api/machine/{machine}/diagnose/troubleshoot/{fix}")
def diagnose_troubleshoot(machine: str, fix: str):
    valid = {"reconfigure_mcps", "kill_conflicts"}
    if fix not in valid:
        return CompactJSONResponse(content={"ok": False, "error": f"Fix must be one of: {', '.join(sorted(valid))}"}, status_code=400)
    result = troubleshoot(machine, fix)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Troubleshoot failed")}, status_code=502)
    return CompactJSONResponse(content=result)

@app.get("/api/machine/{machine}/diagnose/motor")
def diagnose_motor(machine: str):
    result = motor_status(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Motor check failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/audit")
def diagnose_audit(machine: str):
    result = audit_folders(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Audit failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/audit/processes")
def diagnose_audit_processes(machine: str):
    result = audit_processes(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Process audit failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/audit/system")
def diagnose_audit_system(machine: str):
    result = audit_system(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "System audit failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/mcp/scan")
def diagnose_mcp_scan(machine: str):
    result = mcp_scan(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "MCP scan failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/mcp/repair")
def diagnose_mcp_repair(machine: str):
    result = mcp_repair(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "MCP repair failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/mcp/advanced-repair")
def diagnose_mcp_advanced_repair(machine: str):
    result = mcp_advanced_repair(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "MCP advanced repair failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/button/advanced-repair")
def diagnose_button_advanced_repair(machine: str):
    result = button_advanced_repair(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Button advanced repair failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/kill-conflicts")
def diagnose_kill_conflicts(machine: str):
    result = kill_conflicts(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Kill conflicts failed")}, status_code=502)
    return CompactJSONResponse(content=result)


# ── Bluetooth Diagnostic Endpoints ─────────────────────────────────

@app.get("/api/machine/{machine}/diagnose/bt/status")
def diagnose_bt_status(machine: str):
    result = bt_status(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Bluetooth status failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/bt/diagnose")
def diagnose_bt_diagnose(machine: str):
    result = bt_diagnose(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Bluetooth diagnose failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/bt/scan")
def diagnose_bt_scan(machine: str):
    result = bt_scan(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Bluetooth scan failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/bt/reset")
def diagnose_bt_reset(machine: str):
    result = bt_reset(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Bluetooth reset failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/bt/full-reset")
def diagnose_bt_full_reset(machine: str):
    result = bt_full_reset(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Bluetooth full reset failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/bt/recover")
def diagnose_bt_recover(machine: str):
    result = bt_recover(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Bluetooth recovery failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/bt/connection-check")
def diagnose_bt_connection_check(machine: str):
    result = bt_connection_check(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Bluetooth connection check failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/bt/live-log")
def diagnose_bt_live_log(machine: str, duration: int = 120, lines: int = 120):
    result = bt_live_log(machine, duration, lines)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Bluetooth live log failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/bt/fix-crash-loop")
def diagnose_bt_fix_crash_loop(machine: str):
    result = bt_fix_crash_loop(machine)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Bluetooth crash loop fix failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/bt/fix-pairing-popup")
def diagnose_bt_fix_pairing_popup(machine: str):
    result = bt_fix_pairing_popup_safe(machine)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/bt/fix-pairing-popup-persistent")
def diagnose_bt_fix_pairing_popup_persistent(machine: str):
    result = bt_fix_pairing_popup_persistent(machine)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/led/restore")
def diagnose_led_restore(machine: str):
    result = led_control(machine, "restore")
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "LED restore failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.post("/api/machine/{machine}/diagnose/led/diagnose")
def diagnose_led_diagnose(machine: str, deep: bool = False):
    result = led_control(machine, "diagnose", deep=deep)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "LED diagnose failed")}, status_code=502)
    return CompactJSONResponse(content=result)


@app.get("/api/machine/{machine}/diagnose/logs")
def get_diagnostic_logs(machine: str, lines: int = 200):
    result = fetch_app_logs(machine, lines)
    if not result.get("ok"):
        return CompactJSONResponse(content={"ok": False, "error": result.get("error", "Failed to fetch logs")}, status_code=502)
    return CompactJSONResponse(content=result)


# ── Old Data Archive Search ─────────────────────────────────────────


def _get_archive_root():
    machines_json_path = Path(__file__).resolve().parent.parent / "machines.json"
    if not machines_json_path.exists():
        return None
    with machines_json_path.open("r", encoding="utf-8") as f:
        config = json.load(f)
    destination = config.get("destination", "")
    if not destination:
        return None
    archive = Path(destination) / "archive"
    return archive if archive.is_dir() else None


def _calc_avg_bdr(slot_data):
    bdr_data = slot_data.get("bdr_data")
    if isinstance(bdr_data, dict):
        avg = bdr_data.get("avg_bdr")
        if avg is not None:
            return avg, False
    completed = slot_data.get("completed_cycles", [])
    if isinstance(completed, list) and len(completed) > 0:
        values = [c.get("bdr") for c in completed if c.get("bdr") is not None]
        if values:
            return sum(values) / len(values), True
    return None, False


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _count_workouts_from_bdr_cycles(cycles):
    if not cycles:
        return 0
    workouts = 0
    for i, curr in enumerate(cycles):
        start_pct = _num(curr.get("start_pct"))
        if i < len(cycles) - 1:
            next_start = _num((cycles[i + 1] or {}).get("start_pct"))
            drop = start_pct - next_start
            if drop <= 0:
                continue
        else:
            drop = start_pct - _num(curr.get("end_pct"))
        if drop > 0:
            workouts += 1
    return workouts


def _count_workouts_from_completed_cycles(completed_cycles):
    if not completed_cycles or len(completed_cycles) < 2:
        return 0

    groups = []
    current_group = [completed_cycles[0]]
    for i in range(1, len(completed_cycles)):
        prev_cycle = _num((completed_cycles[i - 1] or {}).get("cycle"), 0)
        curr_cycle = _num((completed_cycles[i] or {}).get("cycle"), 0)
        if curr_cycle == 1 and prev_cycle > 1:
            groups.append(current_group)
            current_group = [completed_cycles[i]]
        else:
            current_group.append(completed_cycles[i])
    if current_group:
        groups.append(current_group)

    workouts = 0
    for group in groups:
        for i in range(len(group) - 1):
            curr = group[i] or {}
            nxt = group[i + 1] or {}
            drop = _num(curr.get("start_pct")) - _num(nxt.get("start_pct"))
            if drop > 0:
                workouts += 1
    return workouts


def _calc_completed_workouts(slot_data):
    bdr_data = slot_data.get("bdr_data") or {}
    bdr_state = slot_data.get("bdr_state") or {}
    bdr_cycles = bdr_data.get("cycles") or []
    if bdr_cycles:
        return _count_workouts_from_bdr_cycles(bdr_cycles)
    return _count_workouts_from_completed_cycles(bdr_state.get("completed_cycles") or [])


def _calc_bdr_data_fields(slot_data):
    bdr_data = slot_data.get("bdr_data") or {}
    bdr_state = slot_data.get("bdr_state") or {}
    completed_cycles = bdr_state.get("completed_cycles") or []
    bdr_cycles = bdr_data.get("cycles") or []
    completed_cycle_count = max(len(completed_cycles), len(bdr_cycles))
    avg_bdr, is_estimated = _calc_avg_bdr(slot_data)
    return {
        "avg_bdr": avg_bdr,
        "avg_bdr_is_estimated": is_estimated,
        "stored_avg_bdr": bdr_data.get("stored_avg_bdr"),
        "inter_cycle_avg_bdr": bdr_data.get("inter_cycle_avg_bdr"),
        "test_start": bdr_data.get("test_start"),
        "phase": bdr_state.get("phase") or bdr_data.get("phase_at_finalize"),
        "cycle": bdr_state.get("cycle") or bdr_data.get("final_cycle"),
        "total_cycles": completed_cycle_count,
        "completed_cycles": completed_cycle_count,
        "completed_workouts": _calc_completed_workouts(slot_data),
    }


def _make_archive_entry(snap_file, saved_at, slot_key, slot_data):
    fields = _calc_bdr_data_fields(slot_data)
    return {
        "machine": snap_file.parent.parent.name,
        "date": snap_file.parent.name,
        "time": snap_file.stem,
        "slot": int(slot_key),
        "saved_at": saved_at,
        "serial_number": slot_data.get("serial_number", "").strip(),
        "state": slot_data.get("state", ""),
        "battery_current": slot_data.get("battery_current"),
        "firmware_version": slot_data.get("firmware_version", ""),
        "ring_mac": slot_data.get("ring_mac", ""),
        "ring_name": slot_data.get("ring_name", ""),
        "avg_bdr": fields["avg_bdr"],
        "avg_bdr_is_estimated": fields["avg_bdr_is_estimated"],
        "stored_avg_bdr": fields["stored_avg_bdr"],
        "inter_cycle_avg_bdr": fields["inter_cycle_avg_bdr"],
        "test_start": fields["test_start"],
        "phase": fields["phase"],
        "cycle": fields["cycle"],
        "total_cycles": fields["total_cycles"],
        "completed_cycles": fields["completed_cycles"],
        "completed_workouts": fields["completed_workouts"],
    }


def _archive_entry_key(machine, slot_key):
    return f"{machine}|{slot_key}"


ARCHIVE_INDEX_CACHE_FILE = Path(__file__).resolve().with_name("archive_index_cache.json")
ARCHIVE_SEARCH_FALLBACK_WORKERS = max(8, min(32, (os.cpu_count() or 4) * 2))
ARCHIVE_INDEX_BUILD_WORKERS = max(4, min(16, (os.cpu_count() or 4)))

# Persistent in-memory index: serial -> latest entries per machine+slot
_archive_index = None
_archive_index_lock = threading.Lock()
_archive_index_ready = False
_archive_index_building = False
_archive_index_source = "warming"


def _collect_archive_signature(archive_root):
    archive_root_str = str(archive_root)
    return {
        "archive_root": archive_root_str,
    }


def _load_archive_index_cache(signature):
    if not ARCHIVE_INDEX_CACHE_FILE.exists():
        return None
    try:
        payload = json.loads(ARCHIVE_INDEX_CACHE_FILE.read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    cached_sig = payload.get("signature", {})
    if isinstance(cached_sig, dict) and cached_sig.get("archive_root") == signature.get("archive_root"):
        index = payload.get("index")
        if isinstance(index, dict):
            return index
    return None


def _save_archive_index_cache(signature, index_data):
    payload = {"signature": signature, "index": index_data}
    tmp_path = ARCHIVE_INDEX_CACHE_FILE.with_suffix(".tmp")
    try:
        tmp_path.write_text(
            json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
            encoding="utf-8",
        )
        tmp_path.replace(ARCHIVE_INDEX_CACHE_FILE)
    except OSError as exc:
        print(f"[api] Failed to write archive index cache: {exc}")
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass


def _merge_latest_entries(target, source):
    for key, entry in source.items():
        existing = target.get(key)
        if not existing or entry.get("saved_at", "") > existing.get("saved_at", ""):
            target[key] = entry


def _parse_old_data_serials(values):
    if isinstance(values, str):
        candidates = re.split(r"[\n,;]+", values)
    elif isinstance(values, (list, tuple, set)):
        candidates = []
        for value in values:
            candidates.extend(re.split(r"[\n,;]+", str(value or "")))
    else:
        candidates = [str(values or "")]

    parsed = []
    seen = set()
    for candidate in candidates:
        serial = candidate.strip()
        if not serial:
            continue
        serial_key = serial.lower()
        if serial_key in seen:
            continue
        seen.add(serial_key)
        parsed.append({"serial": serial, "key": serial_key})
    return parsed


def _file_contains_any_serial_fast(file_path, serial_keys_lower):
    """Fast pre-filter using memory-mapped I/O to check if any serial key exists in the file.

    Avoids reading the entire file into a Python string until we know it's a match.
    Returns True if any serial key is found, False otherwise.
    """
    try:
        with open(file_path, "rb") as f:
            try:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
                    for key in serial_keys_lower:
                        if m.find(key.encode("utf-8")) != -1:
                            return True
                    return False
            except (ValueError, OSError):
                # mmap failed (e.g. empty file), fall through to read
                pass
            # Fallback: read content and search
            content_lower = f.read().lower()
            for key in serial_keys_lower:
                if key in content_lower:
                    return True
            return False
    except OSError:
        return False


def _scan_archive_files_for_serial(file_paths, serial_lower):
    serial_keys = [serial_lower]
    results = {}
    for snap_file in file_paths:
        if not _file_contains_any_serial_fast(snap_file, serial_keys):
            continue
        try:
            content = snap_file.read_text("utf-8", errors="replace")
        except OSError:
            continue
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            continue
        saved_at = data.get("saved_at", "")
        for slot_key, slot_data in data.get("slots", {}).items():
            sn = slot_data.get("serial_number", "").strip()
            if not sn or sn in ("--", "N/A") or sn.lower() != serial_lower:
                continue
            key = _archive_entry_key(snap_file.parent.parent.name, slot_key)
            entry = _make_archive_entry(snap_file, saved_at, slot_key, slot_data)
            existing = results.get(key)
            if not existing or saved_at > existing.get("saved_at", ""):
                results[key] = entry
    return results


def _scan_archive_files_for_serials(file_paths, serial_keys):
    results = {serial_key: {} for serial_key in serial_keys}
    if not serial_keys:
        return results

    serial_key_set = set(serial_keys)
    for snap_file in file_paths:
        if not _file_contains_any_serial_fast(snap_file, serial_keys):
            continue
        try:
            content = snap_file.read_text("utf-8", errors="replace")
        except OSError:
            continue
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            continue
        saved_at = data.get("saved_at", "")
        for slot_key, slot_data in data.get("slots", {}).items():
            sn = slot_data.get("serial_number", "").strip()
            serial_key = sn.lower()
            if not sn or sn in ("--", "N/A") or serial_key not in serial_key_set:
                continue
            key = _archive_entry_key(snap_file.parent.parent.name, slot_key)
            entry = _make_archive_entry(snap_file, saved_at, slot_key, slot_data)
            existing = results[serial_key].get(key)
            if not existing or saved_at > existing.get("saved_at", ""):
                results[serial_key][key] = entry
    return results


def _fallback_scan_archive_for_serial(archive_root, serial_lower):
    return _fallback_scan_archive_for_serials(archive_root, [serial_lower]).get(serial_lower, [])


def _fallback_scan_archive_for_serials(archive_root, serial_keys):
    file_paths = []
    for root, _, files in os.walk(str(archive_root)):
        for fname in files:
            if fname.endswith(".json"):
                file_paths.append(Path(root) / fname)
    if not file_paths:
        return {serial_key: [] for serial_key in serial_keys}

    worker_count = min(ARCHIVE_SEARCH_FALLBACK_WORKERS, len(file_paths))
    if worker_count <= 1:
        return {
            serial_key: list(entries.values())
            for serial_key, entries in _scan_archive_files_for_serials(file_paths, serial_keys).items()
        }

    chunk_size = max(1, (len(file_paths) + worker_count - 1) // worker_count)
    merged = {serial_key: {} for serial_key in serial_keys}
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(
                _scan_archive_files_for_serials,
                file_paths[i:i + chunk_size],
                serial_keys,
            )
            for i in range(0, len(file_paths), chunk_size)
        ]
        for future in as_completed(futures):
            try:
                chunk = future.result()
                for serial_key, entries in chunk.items():
                    _merge_latest_entries(merged[serial_key], entries)
            except Exception:
                continue
    return {
        serial_key: list(entries.values())
        for serial_key, entries in merged.items()
    }


def _process_single_archive_file(snap_file, by_serial, db_entries=None):
    """Process one archive JSON file and update the serial index.

    The in-memory index (by_serial) keeps only the latest entry per (machine, slot)
    for fast lookups. SQLite (db_entries) stores ALL entries for complete history.
    Returns the number of entries added/modified in the index.
    """
    try:
        data = json.loads(snap_file.read_text("utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError):
        return 0
    saved_at = data.get("saved_at", "")
    machine_name = snap_file.parent.parent.name
    count = 0
    for slot_key, slot_data in data.get("slots", {}).items():
        sn = slot_data.get("serial_number", "").strip()
        if not sn or sn in ("--", "N/A"):
            continue
        serial_key = sn.lower()
        serial_entries = by_serial.setdefault(serial_key, {})
        entry_key = _archive_entry_key(machine_name, slot_key)
        existing = serial_entries.get(entry_key)
        entry = _make_archive_entry(snap_file, saved_at, slot_key, slot_data)
        if not existing or saved_at > existing.get("saved_at", ""):
            serial_entries[entry_key] = entry
            count += 1
        # Always store ALL entries in SQLite for complete historical data
        if db_entries is not None:
            db_entries.append((entry, str(snap_file)))
    return count


def _add_archive_entry_batch(entries):
    """Batch-insert entries into SQLite in a single transaction."""
    if not entries:
        return
    with _archive_db_lock:
        conn = sqlite3.connect(_archive_db_path)
        c = conn.cursor()
        c.execute("BEGIN")
        for entry, file_path in entries:
            serial = entry.get("serial_number", "")
            c.execute("""
                INSERT OR REPLACE INTO archive_entries 
                (serial_number, serial_lower, file_path, machine, state, machine_avg_bdr, 
                 bdr, firmware_version, ring_mac, ring_name, stored_avg_bdr,
                 inter_cycle_avg_bdr, phase, cycle, completed_workouts,
                 snapshots, total_cycles, completed_cycles, start_time, last_update, saved_at, slot,
                 avg_bdr_is_estimated)
                VALUES (?, lower(?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                serial,
                serial,
                file_path,
                entry.get("machine"),
                entry.get("state"),
                entry.get("avg_bdr"),
                entry.get("battery_current"),
                entry.get("firmware_version"),
                entry.get("ring_mac"),
                entry.get("ring_name"),
                entry.get("stored_avg_bdr"),
                entry.get("inter_cycle_avg_bdr"),
                entry.get("phase"),
                entry.get("cycle"),
                entry.get("completed_workouts"),
                1,
                entry.get("total_cycles"),
                entry.get("completed_cycles"),
                entry.get("test_start"),
                entry.get("saved_at"),
                entry.get("saved_at"),
                entry.get("slot"),
                entry.get("avg_bdr_is_estimated", False),
            ))
        conn.commit()
        conn.close()


def _ingest_single_archive_file(file_path):
    """Parse a single JSON snapshot file and upsert it into the archive DB."""
    try:
        from pathlib import Path
        fp = Path(file_path)
        if not fp.is_file():
            return {"ok": False, "error": "File not found"}
        machine = fp.parent.parent.name
        date_str = fp.parent.name
        time_str = fp.stem
        with open(fp, "r", encoding="utf-8") as f:
            snap = json.load(f)
        slots = snap.get("slots", snap)
        if isinstance(slots, dict):
            entries = []
            for slot_key, slot_data in slots.items():
                bdr_data = slot_data.get("bdr_data") or {}
                bdr_state = slot_data.get("bdr_state") or {}
                completed_cycles = bdr_state.get("completed_cycles") or []
                bdr_cycles = bdr_data.get("cycles") or []
                completed_cycle_count = max(len(completed_cycles), len(bdr_cycles))
                avg_bdr, is_estimated = _calc_avg_bdr(slot_data)
                entry = {
                    "machine": machine,
                    "date": date_str,
                    "time": time_str,
                    "slot": int(slot_key),
                    "saved_at": snap.get("saved_at", f"{date_str}T{time_str}"),
                    "serial_number": slot_data.get("serial_number", "").strip(),
                    "state": slot_data.get("state", ""),
                    "avg_bdr": avg_bdr,
                    "avg_bdr_is_estimated": is_estimated,
                    "battery_current": slot_data.get("battery_current"),
                    "firmware_version": slot_data.get("firmware_version", ""),
                    "ring_mac": slot_data.get("ring_mac", ""),
                    "ring_name": slot_data.get("ring_name", ""),
                    "stored_avg_bdr": bdr_data.get("stored_avg_bdr"),
                    "inter_cycle_avg_bdr": bdr_data.get("inter_cycle_avg_bdr"),
                    "test_start": bdr_data.get("test_start"),
                    "phase": bdr_state.get("phase") or bdr_data.get("phase_at_finalize"),
                    "cycle": bdr_state.get("cycle") or bdr_data.get("final_cycle"),
                    "total_cycles": completed_cycle_count,
                    "completed_cycles": completed_cycle_count,
                    "completed_workouts": _calc_completed_workouts(slot_data),
                }
                entries.append((entry, str(fp)))
            _add_archive_entry_batch(entries)
            return {"ok": True, "entries": len(entries)}
        return {"ok": False, "error": "No slots dict"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _bulk_populate_sqlite_from_index(by_serial):
    """Populate SQLite archive DB from an already-built in-memory index."""
    if not by_serial:
        return
    archive_root = _get_archive_root()
    if not archive_root:
        return
    all_entries = []
    for serial_key, entries in by_serial.items():
        for entry_key, entry in entries.items():
            machine = entry.get("machine", "")
            date = entry.get("date", "")
            time_str = entry.get("time", "")
            slot = entry.get("slot", 0)
            file_path = str(archive_root / machine / date / f"{time_str}.json")
            serial_number = entry.get("serial_number", serial_key)
            all_entries.append((
                serial_number,
                serial_number.lower(),
                file_path,
                machine,
                entry.get("state"),
                entry.get("avg_bdr"),
                entry.get("battery_current"),
                entry.get("firmware_version"),
                entry.get("ring_mac"),
                entry.get("ring_name"),
                entry.get("stored_avg_bdr"),
                entry.get("inter_cycle_avg_bdr"),
                entry.get("phase"),
                entry.get("cycle"),
                entry.get("completed_workouts"),
                1,
                entry.get("total_cycles"),
                entry.get("completed_cycles"),
                entry.get("test_start"),
                entry.get("saved_at"),
                entry.get("saved_at"),
                entry.get("slot"),
                entry.get("avg_bdr_is_estimated", False),
            ))
    if not all_entries:
        return
    BATCH_SIZE = 500
    with _archive_db_lock:
        conn = sqlite3.connect(_archive_db_path)
        c = conn.cursor()
        for i in range(0, len(all_entries), BATCH_SIZE):
            batch = all_entries[i:i + BATCH_SIZE]
            c.execute("BEGIN")
            for row in batch:
                c.execute("""
                    INSERT OR REPLACE INTO archive_entries 
                    (serial_number, serial_lower, file_path, machine, state, machine_avg_bdr, 
                     bdr, firmware_version, ring_mac, ring_name, stored_avg_bdr,
                     inter_cycle_avg_bdr, phase, cycle, completed_workouts,
                     snapshots, total_cycles, completed_cycles, start_time, last_update, saved_at, slot,
                     avg_bdr_is_estimated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, row)
            conn.commit()
        conn.close()


def _search_archive_db_for_serials(serial_keys):
    """Search archive entries directly from SQLite data, no JSON files needed.

    Queries all stored fields from SQLite and constructs result entries
    matching the format produced by the in-memory index or direct scan.
    Searches both serial_number and machine columns so that querying
    by machine name (e.g. "aqc-03") returns all rings that were in that machine.
    """
    if not serial_keys:
        return {}
    conn = sqlite3.connect(_archive_db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    results = {key: [] for key in serial_keys}

    placeholders = ",".join("?" for _ in serial_keys)
    params = serial_keys + serial_keys
    try:
        c.execute(f"""
            SELECT serial_number, file_path, machine, state, machine_avg_bdr,
                   bdr, firmware_version, ring_mac, ring_name, stored_avg_bdr,
                   inter_cycle_avg_bdr, phase, cycle, completed_workouts,
                   snapshots, total_cycles, completed_cycles, start_time,
                   saved_at, slot, last_update,
                   avg_bdr_is_estimated,
                   rn_global, rn_machine
            FROM (
                SELECT *,
                       rn_global,
                       ROW_NUMBER() OVER (
                           PARTITION BY serial_lower, COALESCE(machine,'')
                           ORDER BY saved_at DESC NULLS LAST, last_update DESC NULLS LAST, id DESC
                       ) AS rn_machine
                FROM (
                    SELECT *, ROW_NUMBER() OVER (
                        PARTITION BY serial_lower
                        ORDER BY saved_at DESC NULLS LAST, last_update DESC NULLS LAST, id DESC
                    ) AS rn_global
                    FROM archive_entries
                    WHERE serial_lower IN ({placeholders})
                       OR machine IN ({placeholders})
                ) ranked_global
            ) ranked_both
            WHERE rn_global = 1 OR rn_machine = 1
        """, params)
        rows = c.fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return {}

    if not rows:
        conn.close()
        return results

    serials_need_fb = []
    for row in rows:
        if row["rn_global"] == 1:
            mg_avg = row["machine_avg_bdr"]
            if mg_avg is None or mg_avg == 0.0:
                serials_need_fb.append(row["serial_number"])

    fallback_map = {}
    if serials_need_fb:
        unique_serials = list(set(serials_need_fb))
        fb_placeholders = ",".join("?" for _ in unique_serials)
        try:
            c.execute(f"""
                SELECT serial_number, machine_avg_bdr
                FROM (
                    SELECT serial_number, machine_avg_bdr,
                           ROW_NUMBER() OVER (
                               PARTITION BY serial_number
                               ORDER BY saved_at DESC NULLS LAST, last_update DESC NULLS LAST, id DESC
                           ) AS fb_rn
                    FROM archive_entries
                    WHERE serial_number IN ({fb_placeholders})
                      AND machine_avg_bdr IS NOT NULL AND machine_avg_bdr != 0
                )
                WHERE fb_rn = 1
            """, unique_serials)
            for fb_row in c.fetchall():
                fallback_map[fb_row[0]] = fb_row[1]
        except sqlite3.OperationalError:
            pass

    for row in rows:
        row_dict = dict(row)
        sn = row_dict["serial_number"]
        machine = row_dict["machine"] or ""
        sn_lower = sn.lower()
        machine_lower = machine.lower()

        matched_keys = [k for k in serial_keys if k == sn_lower or k == machine_lower]
        if not matched_keys:
            continue

        rn_global = row_dict["rn_global"]
        rn_machine = row_dict["rn_machine"]
        row_type = "latest" if rn_global == 1 else "history"

        fp = Path(row_dict["file_path"])
        date_str = fp.parent.name
        time_str = fp.stem
        machine_name = machine or fp.parent.parent.name

        mg_avg = row_dict.get("machine_avg_bdr")
        fb_avg = fallback_map.get(sn) if (mg_avg is None or mg_avg == 0.0) else None

        entry = {
            "row_type": row_type,
            "machine": machine_name,
            "date": date_str,
            "time": time_str,
            "slot": row_dict.get("slot"),
            "saved_at": row_dict.get("saved_at") or "",
            "serial_number": sn,
            "state": row_dict.get("state") or "",
            "battery_current": row_dict.get("bdr"),
            "firmware_version": row_dict.get("firmware_version") or "",
            "ring_mac": row_dict.get("ring_mac") or "",
            "ring_name": row_dict.get("ring_name") or "",
            "avg_bdr": mg_avg,
            "fallback_avg_bdr": fb_avg,
            "stored_avg_bdr": row_dict.get("stored_avg_bdr"),
            "inter_cycle_avg_bdr": row_dict.get("inter_cycle_avg_bdr"),
            "test_start": row_dict.get("start_time"),
            "start_time": row_dict.get("start_time"),
            "phase": row_dict.get("phase"),
            "cycle": row_dict.get("cycle"),
            "total_cycles": row_dict.get("total_cycles"),
            "completed_cycles": row_dict.get("completed_cycles"),
            "completed_workouts": row_dict.get("completed_workouts"),
            "file_path": str(fp),
            "last_update": row_dict.get("last_update"),
            "avg_bdr_is_estimated": bool(row_dict.get("avg_bdr_is_estimated")),
        }

        for sk in matched_keys:
            results[sk].append(entry)

    conn.close()
    return results


def _build_archive_index_async():
    global _archive_index, _archive_index_ready, _archive_index_building, _archive_index_source
    with _archive_index_lock:
        if _archive_index_building:
            print("[api] Archive index build already in progress, skipping...")
            return
        _archive_index_building = True

    archive_root = _get_archive_root()
    if not archive_root:
        with _archive_index_lock:
            _archive_index = {}
            _archive_index_ready = True
            _archive_index_building = False
            _archive_index_source = "missing"
        return

    try:
        # Collect all archive JSON files for parallel processing
        all_files = list(archive_root.rglob("*.json"))
        if not all_files:
            with _archive_index_lock:
                _archive_index_building = False
                if not _archive_index_ready:
                    _archive_index_ready = True
            print("[api] No archive files found.")
            return

        workers = ARCHIVE_INDEX_BUILD_WORKERS
        all_db_entries = []

        if workers <= 1 or len(all_files) < 100:
            # Sequential processing for small sets
            db_batch = []
            for snap_file in sorted(all_files):
                _process_single_archive_file(snap_file, {}, db_batch)
                if len(db_batch) >= 200:
                    _add_archive_entry_batch(db_batch)
                    db_batch.clear()
            if db_batch:
                _add_archive_entry_batch(db_batch)
            print(f"[api] Processed {len(all_files)} files sequentially")
        else:
            # Parallel processing with ThreadPoolExecutor
            chunk_size = max(1, (len(all_files) + workers - 1) // workers)
            merge_lock = threading.Lock()
            BATCH_FLUSH = 5000

            def process_chunk(file_chunk):
                local_db = []
                for snap_file in file_chunk:
                    _process_single_archive_file(snap_file, {}, local_db)
                return local_db

            print(f"[api] Processing {len(all_files)} files with {workers} workers ({chunk_size} per chunk)...")
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [
                    executor.submit(process_chunk, all_files[i:i + chunk_size])
                    for i in range(0, len(all_files), chunk_size)
                ]
                completed = 0
                for future in as_completed(futures):
                    try:
                        chunk_db = future.result()
                        with merge_lock:
                            all_db_entries.extend(chunk_db)
                            if len(all_db_entries) >= BATCH_FLUSH:
                                _add_archive_entry_batch(all_db_entries)
                                all_db_entries.clear()
                        completed += 1
                        if completed % 10 == 0:
                            print(f"[api] Index build progress: {completed}/{len(futures)} chunks")
                    except Exception as e:
                        print(f"[api] Index chunk failed: {e}")

            # Write remaining DB entries
            if all_db_entries:
                _add_archive_entry_batch(all_db_entries)
                all_db_entries.clear()
            print(f"[api] Index build complete: {completed} chunks processed")

        with _archive_index_lock:
            _archive_index = None
            if not _archive_index_ready:
                _archive_index_ready = True
            _archive_index_building = False
            _archive_index_source = "rebuilt"
        print(f"[api] Archive index rebuilt from {len(all_files)} files, in-memory index freed")
    except Exception as exc:
        with _archive_index_lock:
            _archive_index_building = False
        print(f"[api] Archive index build failed: {exc}")


def _ensure_archive_index():
    global _archive_index_source
    if _archive_index_ready:
        return True
    with _archive_index_lock:
        if _archive_index_ready:
            return True
        if not _archive_index_building:
            _archive_index_source = "warming"
            thread = threading.Thread(target=_build_archive_index_async, daemon=True)
            thread.start()
    return False


def _await_archive_index(timeout_seconds=60):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with _archive_index_lock:
            if _archive_index_ready:
                return True
        time.sleep(0.05)
    return False


def _find_latest_snapshot_for_serial(serial_number, machine, archive_root, stale_saved_at=None):
    try:
        machine_dir = Path(archive_root) / machine
        if not machine_dir.is_dir():
            return None
        stale_dt = None
        if stale_saved_at:
            try:
                stale_dt = datetime.fromisoformat(stale_saved_at)
            except (ValueError, TypeError):
                pass
        date_dirs = sorted([d for d in machine_dir.iterdir() if d.is_dir()], reverse=True)
        for date_dir in date_dirs:
            if stale_dt and date_dir.name < stale_dt.strftime("%Y-%m-%d"):
                continue
            files = sorted(date_dir.glob("*.json"), reverse=True)
            for f in files:
                if stale_dt and date_dir.name == stale_dt.strftime("%Y-%m-%d"):
                    ft = f.stem.replace("-", ":")
                    try:
                        ft_dt = datetime.strptime(ft, "%H:%M:%S").time()
                        if ft_dt <= stale_dt.time():
                            continue
                    except (ValueError, TypeError):
                        pass
                try:
                    with open(f, "r", encoding="utf-8") as fh:
                        snap = json.load(fh)
                    slots = snap.get("slots", snap)
                    if not isinstance(slots, dict):
                        continue
                    for k, v in slots.items():
                        sn = v.get("serial_number", "").strip().lower()
                        if sn == serial_number.lower():
                            bd = v.get("bdr_data") or {}
                            bs = v.get("bdr_state") or {}
                            cc = v.get("completed_cycles") or []
                            avg_bdr, is_est = _calc_avg_bdr(v)
                            return {
                                "machine": machine,
                                "slot": int(k),
                                "state": v.get("state", ""),
                                "serial_number": v.get("serial_number", ""),
                                "avg_bdr": avg_bdr,
                                "avg_bdr_is_estimated": is_est,
                                "stored_avg_bdr": bd.get("stored_avg_bdr"),
                                "inter_cycle_avg_bdr": bd.get("inter_cycle_avg_bdr"),
                                "phase": bs.get("phase") or bd.get("phase_at_finalize"),
                                "cycle": bs.get("cycle") or bd.get("final_cycle"),
                                "test_start": bd.get("test_start"),
                                "start_time": bd.get("test_start"),
                                "battery_current": v.get("battery_current"),
                                "firmware_version": v.get("firmware_version", ""),
                                "ring_mac": v.get("ring_mac", ""),
                                "ring_name": v.get("ring_name", ""),
                                "saved_at": snap.get("saved_at", f"{date_dir.name}T{f.stem}"),
                                "completed_cycles": len(cc),
                                "total_cycles": len(cc),
                                "date": date_dir.name,
                                "time": f.stem,
                                "file_path": str(f),
                            }
                except (json.JSONDecodeError, OSError):
                    continue
    except OSError:
        pass
    return None


def _aggregate_archive_results(raw, archive_root=None):
    latest = None
    history = []

    for record in raw:
        mg_avg = record.get("avg_bdr")
        fallback = record.get("fallback_avg_bdr")
        state = record.get("state", "")
        is_running = "running" in state.lower() if state else False

        is_null_or_bad = mg_avg is None or mg_avg == 0.0 or (mg_avg is not None and mg_avg < 0)

        use_fallback = (
            is_null_or_bad
            and fallback is not None and fallback != 0.0
            and not is_running
        )
        if use_fallback:
            record["avg_bdr"] = fallback
            record["avg_bdr_is_stale"] = True
        else:
            record["avg_bdr_is_stale"] = True if is_null_or_bad else False

        if record.get("row_type") == "latest":
            latest = record
        else:
            history.append(record)

    if not latest:
        return []

    latest["state"] = latest.get("state", "")

    if archive_root:
        for rec in [latest] + history:
            is_stale = rec.get("avg_bdr_is_stale", False) or rec.get("avg_bdr") is None or rec.get("avg_bdr") == 0.0
            if is_stale:
                snap_serial = rec.get("serial_number", "")
                snap_machine = rec.get("machine", "")
                snap_saved = rec.get("saved_at", "")
                if snap_serial and snap_machine:
                    jsnap = _find_latest_snapshot_for_serial(snap_serial, snap_machine, archive_root, snap_saved)
                    if jsnap and jsnap.get("avg_bdr") is not None:
                        rec.update(jsnap)
                        rec["avg_bdr_is_stale"] = False

    is_stale_latest = latest.get("avg_bdr_is_stale", False) or latest.get("avg_bdr") is None or latest.get("avg_bdr") == 0.0
    if is_stale_latest:
        latest_state = latest.get("state", "")
        if not latest_state.strip():
            for h in sorted(history, key=lambda r: r.get("saved_at", ""), reverse=True):
                hs = h.get("state", "")
                if hs and "bdr" not in hs.lower() and hs.strip():
                    latest["state"] = hs
                    break

    def _make_row(rec, row_type):
        avg = rec.get("avg_bdr")
        return {
            "row_type": row_type,
            "machine": rec["machine"],
            "date": rec.get("date", ""),
            "time": rec.get("time", ""),
            "slot": rec.get("slot"),
            "saved_at": rec.get("saved_at", ""),
            "serial_number": rec.get("serial_number", ""),
            "state": rec.get("state", ""),
            "battery_current": rec.get("battery_current"),
            "firmware_version": rec.get("firmware_version", ""),
            "ring_mac": rec.get("ring_mac", ""),
            "ring_name": rec.get("ring_name", ""),
            "avg_bdr": avg,
            "machine_avg_bdr": avg,
            "avg_bdr_is_stale": rec.get("avg_bdr_is_stale", False),
            "avg_bdr_is_estimated": rec.get("avg_bdr_is_estimated", False),
            "stored_avg_bdr": rec.get("stored_avg_bdr"),
            "inter_cycle_avg_bdr": rec.get("inter_cycle_avg_bdr"),
            "test_start": rec.get("test_start"),
            "phase": rec.get("phase"),
            "cycle": rec.get("cycle"),
            "total_cycles": rec.get("total_cycles"),
            "completed_cycles": rec.get("completed_cycles", rec.get("total_cycles", 0)),
            "snapshots": 1,
            "start_time": rec.get("start_time"),
            "last_update": rec.get("saved_at", ""),
            "file_path": rec.get("file_path", ""),
        }

    rows = [_make_row(latest, "latest")]
    for h in history:
        rows.append(_make_row(h, "history"))

    return rows


def _search_old_data_payload(serial_values):
    archive_root = _get_archive_root()
    if not archive_root:
        return {"ok": False, "error": "Archive directory not found"}

    parsed_serials = _parse_old_data_serials(serial_values)
    if not parsed_serials:
        return {"ok": False, "error": "At least one valid serial number is required"}

    # Background safety-net rescan runs every 30 min via _reindex_archive_background.
    # New files are ingested immediately via main.py -> POST /api/old-data/ingest-file,
    # so no need to trigger a full rescan here.

    serial_keys = [item["key"] for item in parsed_serials]
    db_results = _search_archive_db_for_serials(serial_keys)

    results = []
    for item in parsed_serials:
        serial_results = _aggregate_archive_results(db_results.get(item["key"], []), archive_root)
        for record in serial_results:
            enriched = dict(record)
            enriched["query_serial"] = item["serial"]
            results.append(enriched)

    total = len(results)
    is_multi_serial = len(parsed_serials) > 1

    payload = {
        "ok": True,
        "count": total,
        "results": results,
        "indexed": True,
        "index_source": "sqlite",
        "multi_serial": is_multi_serial,
        "serials": [item["serial"] for item in parsed_serials],
    }
    if not is_multi_serial:
        payload["serial"] = parsed_serials[0]["serial"]
    return payload


@app.get("/api/old-data/search/{serial:path}")
@app.get("/api/old-data/search/{serial:path}/")
def search_old_data(serial: str):
    try:
        return CompactJSONResponse(content=_search_old_data_payload([serial]))
    except Exception as e:
        import traceback
        print(f"[api] ERROR in single-serial search: {str(e)}")
        print(traceback.format_exc())
        return CompactJSONResponse(content={"ok": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)


@app.post("/api/old-data/search")
@app.post("/api/old-data/search/")
async def search_old_data_batch(request: Request):
    try:
        payload = await request.json()
        print(f"[api] Received search payload: {payload}")
        serial_values = payload.get("serials") if isinstance(payload, dict) else None
        result = _search_old_data_payload(serial_values)
        return CompactJSONResponse(content=result)
    except Exception as e:
        import traceback
        print(f"[api] ERROR in multi-serial search: {str(e)}")
        print(traceback.format_exc())
        return CompactJSONResponse(content={"ok": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)


@app.post("/api/old-data/ingest-file")
async def ingest_archive_file(request: Request):
    """Immediately parse a single archive JSON file and upsert into SQLite."""
    try:
        payload = await request.json()
        file_path = payload.get("file_path") if isinstance(payload, dict) else None
        if not file_path:
            return CompactJSONResponse(content={"ok": False, "error": "file_path required"}, status_code=400)
        result = _ingest_single_archive_file(file_path)
        return CompactJSONResponse(content=result)
    except Exception as e:
        import traceback
        return CompactJSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


if __name__ == "__main__":
    # NB: DB init, PG init, file sync, and initial archive index build
    # are handled by the startup_event (@app.on_event("startup")).
    
    # Background: prune old archive JSON files once per day
    def _prune_archive_files_background():
        while True:
            try:
                pruned_count = _prune_old_archive_files(days=2)
                if pruned_count > 0:
                    print(f"[api] Pruned {pruned_count} old archive files")
            except Exception as e:
                print(f"[api] Error pruning archive files: {e}")
            time.sleep(86400)
    
    pruning_thread = threading.Thread(target=_prune_archive_files_background, daemon=True)
    pruning_thread.start()
    print("[api] Started background archive pruning thread")
    
    # Background: periodically refresh SQLite from JSON files
    # so newly archived JSON files are picked up without a restart.
    # Increased to 30 min since we now search SQLite directly (no in-memory index).
    # The guard in _build_archive_index_async prevents concurrent runs.
    def _reindex_archive_background():
        initial_delay = 120
        interval = 1800
        time.sleep(initial_delay)
        while True:
            try:
                print("[api] Background archive index refresh starting...")
                _build_archive_index_async()
                print("[api] Background archive index refresh complete")
            except Exception as e:
                print(f"[api] Error during background archive index refresh: {e}")
            time.sleep(interval)
    
    reindex_thread = threading.Thread(target=_reindex_archive_background, daemon=True)
    reindex_thread.start()
    print("[api] Started background archive index refresh thread (every 30 min)")
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

