import json
import mmap
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import urllib.error
import urllib.parse
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
    wait_for_pg,
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
                try:
                    file_mtime = json_file.stat().st_mtime
                except OSError:
                    continue
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
    print("Initializing PostgreSQL...")
    if wait_for_pg():
        try:
            init_pg()
            print("PostgreSQL initialized.")
        except Exception as e:
            print(f"PostgreSQL init failed: {e}")
            print("PostgreSQL not available - data will not be served.")
    else:
        print("PostgreSQL not available - data will not be served.")
    thread = threading.Thread(target=_background_file_sync, daemon=True)
    thread.start()
    print(f"Background file sync started (every {FILE_SYNC_INTERVAL}s).")

    # Background: prune old archive JSON files once per day
    def _prune_archive_files_background():
        while True:
            try:
                pruned_count = _prune_old_archive_files(days=3)
                if pruned_count > 0:
                    print(f"[api] Pruned {pruned_count} old archive files")
            except Exception as e:
                print(f"[api] Error pruning archive files: {e}")
            time.sleep(86400)

    pruning_thread = threading.Thread(target=_prune_archive_files_background, daemon=True)
    pruning_thread.start()
    print("[api] Started background archive pruning thread")

    # Background: prune ring_status rows older than 30 days, once per day
    def _prune_ring_status_background():
        while True:
            try:
                if pg_available():
                    conn = get_connection()
                    try:
                        with conn.cursor() as cur:
                            cur.execute(
                                "DELETE FROM ring_status WHERE saved_at < NOW() - INTERVAL '30 days'"
                            )
                            deleted = cur.rowcount
                        conn.commit()
                        if deleted > 0:
                            print(f"[api] Pruned {deleted} stale ring_status rows (>30 days)")
                    finally:
                        conn.close()
            except Exception as e:
                print(f"[api] Error pruning ring_status: {e}")
            time.sleep(86400)

    ring_prune_thread = threading.Thread(target=_prune_ring_status_background, daemon=True)
    ring_prune_thread.start()
    print("[api] Started background ring_status pruning thread (30-day retention)")

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


@app.get("/api/machines/config")
def list_machines_config():
    machines_json_path = Path(__file__).resolve().parent.parent / "machines.json"
    machines = []
    if machines_json_path.exists():
        with machines_json_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
            for m in config.get("machines", []):
                machines.append({
                    "name": m.get("name", ""),
                    "removed_slots": m.get("removed_slots", []),
                })
    return CompactJSONResponse(content={"machines": machines})


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


ASSIGNED_TIMES_LOCK = threading.Lock()
ASSIGNED_TIMES_PATH = Path(__file__).resolve().parent.parent / "assigned_times.json"
ASSIGNED_HISTORY_PATH = Path(__file__).resolve().parent.parent / "assigned_history.json"


def _load_assigned_times():
    try:
        if ASSIGNED_TIMES_PATH.exists():
            with ASSIGNED_TIMES_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[API] Error loading assigned_times.json: {e}")
    return {}


def _save_assigned_times(data):
    try:
        with ASSIGNED_TIMES_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[API] Error saving assigned_times.json: {e}")


def _load_assigned_history():
    try:
        if ASSIGNED_HISTORY_PATH.exists():
            with ASSIGNED_HISTORY_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[API] Error loading assigned_history.json: {e}")
    return []


def _save_assigned_history(data):
    try:
        with ASSIGNED_HISTORY_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[API] Error saving assigned_history.json: {e}")


@app.get("/api/rings/assigned-times")
def get_assigned_times():
    return CompactJSONResponse(content=_load_assigned_times())


@app.get("/api/rings/assigned-history")
def get_assigned_history():
    return CompactJSONResponse(content={"events": _load_assigned_history()})


@app.post("/api/rings/assigned-times")
async def set_assigned_times(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    entries = payload.get("entries") or []
    with ASSIGNED_TIMES_LOCK:
        data = _load_assigned_times()
        history = _load_assigned_history()
        changed = False
        for e in entries:
            machine = e.get("machine")
            slot = e.get("slot")
            serial = e.get("serial")
            ts = e.get("ts")
            if not machine or slot is None or not serial or not ts:
                continue
            cur = data.get(machine, {}).get(str(slot))
            if not cur or cur.get("serial") != serial:
                data.setdefault(machine, {})[str(slot)] = {"serial": serial, "ts": ts}
                history.append({"machine": machine, "slot": slot, "serial": serial, "ts": ts})
                changed = True
        if changed:
            _save_assigned_times(data)
            _save_assigned_history(history)
    return CompactJSONResponse(content={"ok": True})


STATUS_TIMES_LOCK = threading.Lock()
STATUS_TIMES_PATH = Path(__file__).resolve().parent.parent / "status_times.json"
STATUS_HISTORY_PATH = Path(__file__).resolve().parent.parent / "status_history.json"


def _load_status_times():
    try:
        if STATUS_TIMES_PATH.exists():
            with STATUS_TIMES_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[API] Error loading status_times.json: {e}")
    return {}


def _save_status_times(data):
    try:
        with STATUS_TIMES_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[API] Error saving status_times.json: {e}")


def _load_status_history():
    try:
        if STATUS_HISTORY_PATH.exists():
            with STATUS_HISTORY_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[API] Error loading status_history.json: {e}")
    return []


def _save_status_history(data):
    try:
        with STATUS_HISTORY_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[API] Error saving status_history.json: {e}")


@app.get("/api/rings/status-times")
def get_status_times():
    return CompactJSONResponse(content=_load_status_times())


@app.get("/api/rings/status-history")
def get_status_history():
    return CompactJSONResponse(content={"events": _load_status_history()})


@app.post("/api/rings/status-times")
async def set_status_times(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    entries = payload.get("entries") or []
    with STATUS_TIMES_LOCK:
        data = _load_status_times()
        history = _load_status_history()
        changed = False
        for e in entries:
            machine = e.get("machine")
            slot = e.get("slot")
            serial = e.get("serial")
            status = str(e.get("status") or "").upper()
            ts = e.get("ts")
            if not machine or slot is None or not serial or not ts:
                continue
            if status not in ("PASSED", "FAILED"):
                continue
            cur = data.get(machine, {}).get(str(slot))
            if not cur or cur.get("serial") != serial or cur.get("status") != status:
                data.setdefault(machine, {})[str(slot)] = {"serial": serial, "status": status, "ts": ts}
                history.append({"machine": machine, "slot": slot, "serial": serial, "status": status, "ts": ts})
                changed = True
        if changed:
            _save_status_times(data)
            _save_status_history(history)
    return CompactJSONResponse(content={"ok": True})


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


# ── RTO Category — Google Sheet Configuration ─────────────────────

RTO_CONFIG_LOCK = threading.Lock()
RTO_CONFIG_PATH = Path(__file__).resolve().parent.parent / "rto_config.json"


def _load_rto_config():
    default = {
        "ok": False,
        "url": "",
        "sheet": "",
        "column": "",
        "serials": [],
        "count": 0,
        "updated_at": None,
    }
    try:
        if RTO_CONFIG_PATH.exists():
            with RTO_CONFIG_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                default.update(data)
    except Exception as e:
        print(f"[api] Error loading rto_config.json: {e}")
    return default


def _save_rto_config(data):
    try:
        with RTO_CONFIG_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[api] Error saving rto_config.json: {e}")


def _fetch_url_bytes(url, timeout=30):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BDR-Dashboard/1.0",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _find_sheet_column_index(headers, column_name):
    """Locate a column by header label (case-insensitive) or A1 letter."""
    target = str(column_name or "").strip()
    if not target:
        return None
    lower = target.lower()
    clean = lower.strip('"').strip("'")
    for i, h in enumerate(headers):
        hv = str(h or "").strip().strip('"').strip("'").lower()
        if hv == lower or hv == clean:
            return i
    if len(clean) == 1 and clean.isalpha():
        idx = ord(clean.upper()) - ord("A")
        if 0 <= idx < 26:
            return idx
    return None


def _collect_column_serials(rows, idx):
    serials = []
    seen = set()
    for row in rows:
        if idx >= len(row):
            continue
        cell = row[idx]
        if cell is None:
            continue
        if isinstance(cell, dict):
            cell = cell.get("v")
        if cell is None:
            continue
        sv = str(cell).strip()
        if not sv:
            continue
        key = sv.upper()
        if key in seen:
            continue
        seen.add(key)
        serials.append(sv)
    return serials


def _fetch_serials_gviz(token, sheet_name, column_name):
    """Fetch a public sheet via the Google Visualization JSONP endpoint."""
    params = {"tqx": "out:json"}
    if sheet_name:
        params["sheet"] = sheet_name
    url = "https://docs.google.com/spreadsheets/d/%s/gviz/tq?%s" % (
        token,
        urllib.parse.urlencode(params),
    )
    text = _fetch_url_bytes(url).decode("utf-8", errors="replace")
    start = text.find("(")
    end = text.rfind(")")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Unexpected response from Google Sheets (gviz)")
    payload = json.loads(text[start + 1 : end])
    if payload.get("status") != "ok":
        raise ValueError("Google Sheets returned status: %s" % payload.get("status", "unknown"))
    table = payload.get("table", {}) or {}
    headers = [c.get("label") or c.get("type") for c in table.get("cols", [])]
    idx = _find_sheet_column_index(headers, column_name)
    if idx is None:
        raise ValueError(
            "Column '%s' not found. Available columns: %s"
            % (column_name, ", ".join(str(h) for h in headers[:20]) or "(none)")
        )
    rows = [r.get("c") or [] for r in table.get("rows", [])]
    return _collect_column_serials(rows, idx)


def _fetch_serials_csv(token, sheet_name, column_name, published=False):
    """Fetch a public sheet as CSV (used as fallback / for published sheets)."""
    import csv as _csv
    import io as _io

    if published:
        url = "https://docs.google.com/spreadsheets/d/e/%s/pub?output=csv" % token
    else:
        params = {"tqx": "out:csv"}
        if sheet_name:
            params["sheet"] = sheet_name
        url = "https://docs.google.com/spreadsheets/d/%s/gviz/tq?%s" % (
            token,
            urllib.parse.urlencode(params),
        )
    text = _fetch_url_bytes(url).decode("utf-8", errors="replace")
    reader = _csv.reader(_io.StringIO(text))
    all_rows = [row for row in reader if any((c or "").strip() for c in row)]
    if not all_rows:
        raise ValueError("The Google Sheet returned no data")
    headers = all_rows[0]
    idx = _find_sheet_column_index(headers, column_name)
    if idx is None:
        raise ValueError(
            "Column '%s' not found. Available columns: %s"
            % (column_name, ", ".join(str(h) for h in headers[:20]) or "(none)")
        )
    return _collect_column_serials(all_rows[1:], idx)


def _fetch_serials_for_config(url, sheet_name, column_name):
    match = re.search(r"/d/(?:e/)?([A-Za-z0-9_\-]+)", url or "")
    if not match:
        raise ValueError(
            "Could not find a Google Sheet ID in the URL. Use the standard share link like "
            "https://docs.google.com/spreadsheets/d/<ID>/edit"
        )
    token = match.group(1)
    published = bool(re.search(r"/d/e/", url or ""))

    if published:
        return _fetch_serials_csv(token, sheet_name, column_name, published=True)

    errors = []
    try:
        return _fetch_serials_gviz(token, sheet_name, column_name)
    except Exception as e:
        errors.append(str(e))
    try:
        return _fetch_serials_csv(token, sheet_name, column_name)
    except Exception as e:
        errors.append(str(e))
    raise ValueError("; ".join(errors) or "Failed to fetch the Google Sheet")


@app.get("/api/settings/rto")
def get_rto_settings():
    with RTO_CONFIG_LOCK:
        cfg = _load_rto_config()
    return CompactJSONResponse(content=cfg)


@app.post("/api/settings/rto")
async def set_rto_settings(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    if payload.get("clear"):
        cfg = {
            "ok": False,
            "url": "",
            "sheet": "",
            "column": "",
            "serials": [],
            "count": 0,
            "updated_at": None,
        }
        with RTO_CONFIG_LOCK:
            _save_rto_config(cfg)
        return CompactJSONResponse(content={**cfg, "cleared": True})

    url = str(payload.get("url") or "").strip()
    sheet = str(payload.get("sheet") or "").strip()
    column = str(payload.get("column") or "").strip()
    if not url or not column:
        return CompactJSONResponse(
            content={"ok": False, "error": "Google Sheet URL and Column Name are required."},
            status_code=400,
        )

    try:
        serials = _fetch_serials_for_config(url, sheet, column)
    except ValueError as e:
        return CompactJSONResponse(content={"ok": False, "error": str(e)}, status_code=400)
    except Exception as e:
        return CompactJSONResponse(
            content={"ok": False, "error": "Failed to fetch Google Sheet: %s" % e},
            status_code=502,
        )

    cfg = {
        "ok": True,
        "url": url,
        "sheet": sheet,
        "column": column,
        "serials": serials,
        "count": len(serials),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    with RTO_CONFIG_LOCK:
        _save_rto_config(cfg)
    return CompactJSONResponse(content=cfg)


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
    completed = slot_data.get("completed_cycles")
    if not completed:
        bdr_state = slot_data.get("bdr_state") or {}
        completed = bdr_state.get("completed_cycles") or []
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
        "start_time": fields["test_start"],
        "phase": fields["phase"],
        "cycle": fields["cycle"],
        "total_cycles": fields["total_cycles"],
        "completed_cycles": fields["completed_cycles"],
        "completed_workouts": fields["completed_workouts"],
    }


def _archive_entry_key(machine, slot_key):
    return f"{machine}|{slot_key}"



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


def _fallback_scan_archive_for_serials(archive_root, serial_keys, file_list=None):
    if file_list is not None:
        file_paths = file_list
    else:
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


def _search_ring_status_for_serials(serial_keys):
    """Query ring_status (latest-state table) for serials or machine names.

    Returns a dict keyed by each serial_key, each value a list of entries
    whose shape matches the old merged response (see _search_old_data_payload).
    """
    if not serial_keys:
        return {}
    try:
        from postgres_db import get_connection
        import psycopg2.extras
        pg_conn = get_connection()
        try:
            with pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM   ring_status
                    WHERE  LOWER(serial_number) = ANY(%s)
                       OR  LOWER(machine)       = ANY(%s)
                    ORDER  BY serial_number, machine
                    """,
                    (serial_keys, serial_keys),
                )
                rows = cur.fetchall()
        finally:
            pg_conn.close()
    except Exception as e:
        print(f"[api] ring_status query error: {e}")
        return {}

    results_map = {key: [] for key in serial_keys}
    for row in rows:
        rec = dict(row)
        sn_lower = str(rec.get("serial_number", "")).lower()
        machine  = rec.get("machine", "")

        # Determine which serial_keys this row matches
        matched_keys = [k for k in serial_keys if k == sn_lower or k == machine.lower()]
        if not matched_keys:
            continue

        # saved_at may be a datetime object coming from psycopg2; normalise to ISO string
        saved_at_val = rec.get("saved_at")
        if saved_at_val is not None and hasattr(saved_at_val, "isoformat"):
            saved_at_val = saved_at_val.isoformat()
        elif saved_at_val is not None:
            saved_at_val = str(saved_at_val)

        phase_start_val = rec.get("phase_start_time")
        if phase_start_val is not None and hasattr(phase_start_val, "timestamp"):
            phase_start_val = phase_start_val.timestamp()
        elif phase_start_val is not None:
            try:
                phase_start_val = float(phase_start_val)
            except (TypeError, ValueError):
                phase_start_val = None

        entry = {
            "type":                    "latest",
            "serial_number":           rec.get("serial_number", ""),
            "machine":                 machine,
            "slot":                    rec.get("slot"),
            "state":                   rec.get("state", "") or "",
            "battery_current":         rec.get("battery_current"),
            "firmware_version":        rec.get("firmware_version", "") or "",
            "ring_mac":                rec.get("ring_mac", "") or "",
            "ring_name":               rec.get("ring_name", "") or "",
            "avg_bdr":                 rec.get("avg_bdr"),
            "machine_avg_bdr":         rec.get("avg_bdr"),
            "avg_bdr_is_stale":        False,
            "avg_bdr_is_estimated":    False,
            "stored_avg_bdr":          None,
            "inter_cycle_avg_bdr":     None,
            "test_start":              phase_start_val,
            "phase":                   rec.get("phase", "") or "",
            "cycle":                   rec.get("cycle"),
            "snapshots":               1,
            "total_cycles":            rec.get("cycle"),
            "completed_cycles":        rec.get("cycle"),
            "completed_workouts":      None,
            "start_time":              phase_start_val,
            "last_update":             saved_at_val or "",
            "saved_at":                saved_at_val or "",
            "file_path":               rec.get("file_path", "") or "",
        }

        for sk in matched_keys:
            results_map[sk].append(entry)

    return results_map


def _search_old_data_payload(serial_values, use_new_table=False):
    from data.postgres_db import search_archive_in_pg
    parsed_serials = _parse_old_data_serials(serial_values)
    if not parsed_serials:
        return {"ok": False, "error": "At least one valid serial number is required"}

    serial_keys = [item["key"] for item in parsed_serials]

    if use_new_table:
        # ── New path: ring_status (single query, no merge needed) ──────────────
        rs_results = _search_ring_status_for_serials(serial_keys)

        results = []
        for item in parsed_serials:
            key = item["key"]
            for record in rs_results.get(key, []):
                enriched = dict(record)
                enriched["query_serial"] = item["serial"]
                results.append(enriched)

        total = len(results)
        is_multi_serial = len(parsed_serials) > 1
        distinct_machines = len({r.get("machine", "") for r in results})
        print(f"[api] ring_status search for {serial_keys}: "
              f"{total} record(s) across {distinct_machines} machine(s)")

        payload = {
            "ok": True,
            "count": total,
            "results": results,
            "indexed": True,
            "index_source": "ring_status",
            "multi_serial": is_multi_serial,
            "serials": [item["serial"] for item in parsed_serials],
        }
        if not is_multi_serial:
            payload["serial"] = parsed_serials[0]["serial"]
        return payload

    # ── PG-only path ──────────────────────────────────────────────────────
    pg_results = search_archive_in_pg(serial_keys)

    results = []
    for item in parsed_serials:
        key = item["key"]
        for record in pg_results.get(key, []):
            enriched = dict(record)
            enriched["query_serial"] = item["serial"]
            results.append(enriched)

    total = len(results)
    is_multi_serial = len(parsed_serials) > 1
    distinct_machines = len({r.get("machine", "") for r in results})
    print(f"[api] Old-data search for {serial_keys}: "
          f"{total} record(s) across {distinct_machines} machine(s) "
          f"(pg={total})")

    payload = {
        "ok": True,
        "count": total,
        "results": results,
        "indexed": True,
        "index_source": "pg",
        "multi_serial": is_multi_serial,
        "serials": [item["serial"] for item in parsed_serials],
    }
    if not is_multi_serial:
        payload["serial"] = parsed_serials[0]["serial"]
    return payload


@app.get("/api/old-data/search/{serial:path}")
@app.get("/api/old-data/search/{serial:path}/")
async def search_old_data(serial: str, request: Request):
    try:
        use_new = request.query_params.get("use_new_table", "").lower() in ("1", "true", "yes")
        return CompactJSONResponse(content=_search_old_data_payload([serial], use_new_table=use_new))
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
        use_new = payload.get("use_new_table", False) if isinstance(payload, dict) else False
        result = _search_old_data_payload(serial_values, use_new_table=bool(use_new))
        return CompactJSONResponse(content=result)
    except Exception as e:
        import traceback
        print(f"[api] ERROR in multi-serial search: {str(e)}")
        print(traceback.format_exc())
        return CompactJSONResponse(content={"ok": False, "error": str(e), "traceback": traceback.format_exc()}, status_code=500)


@app.post("/api/old-data/ingest-file")
async def ingest_archive_file(request: Request):
    """Immediately parse a single archive JSON file and upsert into PostgreSQL."""
    try:
        from data.postgres_db import ingest_archive_to_pg
        payload = await request.json()
        file_path = payload.get("file_path") if isinstance(payload, dict) else None
        if not file_path:
            return CompactJSONResponse(content={"ok": False, "error": "file_path required"}, status_code=400)
            
        import json
        from pathlib import Path
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        slots = data.get("slots", {})
        if not isinstance(slots, dict):
            return CompactJSONResponse(content={"ok": True, "msg": "No slots found"})
            
        saved_at = data.get("saved_at", "")
        file_path_obj = Path(file_path)
        
        for slot_id, slot_data in slots.items():
            if isinstance(slot_data, dict) and "serial_number" in slot_data:
                enriched_entry = _make_archive_entry(file_path_obj, saved_at, slot_id, slot_data)
                ingest_archive_to_pg(enriched_entry)

        # Upsert into ring_status (latest-state table)
        try:
            from ring_status import ingest_file_to_ring_status
            pg_conn = get_connection()
            ingest_file_to_ring_status(pg_conn, file_path)
            pg_conn.commit()
            pg_conn.close()
        except Exception:
            pass

        return CompactJSONResponse(content={"ok": True})
    except Exception as e:
        import traceback
        return CompactJSONResponse(content={"ok": False, "error": str(e)}, status_code=500)


if __name__ == "__main__":
    # NB: All background threads (pruning, ring_status cleanup)
    # are now started in startup_event() so they run on every launch path.
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

