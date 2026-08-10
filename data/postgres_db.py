import json
import os
import re
import threading
import traceback
import time
from datetime import datetime, timezone
from pathlib import Path

PG_CONFIG = {
    "host": os.environ.get("PG_HOST", "127.0.0.1"),
    "port": int(os.environ.get("PG_PORT", 5432)),
    "dbname": os.environ.get("PG_DB", "bdr_dashboard"),
    "user": os.environ.get("PG_USER", "postgres"),
    "password": os.environ.get("PG_PASSWORD", "postgres"),
    "connect_timeout": 3,
    "options": "-c statement_timeout=15000",
    "keepalives": 1,
    "keepalives_idle": 5,
    "keepalives_interval": 2,
    "keepalives_count": 2,
}

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
    HAS_PSYCOPG2 = True
except ImportError:
    psycopg2 = None
    HAS_PSYCOPG2 = False

_pg_available = None
_PG_RECHECK_AFTER = 15  # Check every 15 seconds
_last_pg_check = 0

# Simple connection pool for reads — avoids creating a new TCP connection per request.
_PG_POOL = None
_PG_POOL_LOCK = threading.Lock()

def _get_pool():
    global _PG_POOL
    if _PG_POOL is None:
        with _PG_POOL_LOCK:
            if _PG_POOL is None:
                _PG_POOL = psycopg2.pool.SimpleConnectionPool(1, 5, **PG_CONFIG)
    return _PG_POOL

class _PooledConnection:
    """Wraps a psycopg2 connection so that .close() returns it to the pool."""
    def __init__(self, conn):
        self._conn = conn
    def __getattr__(self, name):
        return getattr(self._conn, name)
    def close(self):
        pool = _get_pool()
        try:
            # Verify the connection is still alive before returning it
            cur = self._conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            pool.putconn(self._conn)
        except Exception:
            try:
                pool.putconn(self._conn, close=True)
            except Exception:
                pass

def is_available():
    global _pg_available, _last_pg_check
    now = time.time()
    
    if not HAS_PSYCOPG2:
        raise RuntimeError("PostgreSQL driver (psycopg2) is not installed. Database is required.")
        
    if _pg_available is None or (now - _last_pg_check) >= _PG_RECHECK_AFTER:
        try:
            conn = psycopg2.connect(**PG_CONFIG)
            conn.close()
            _pg_available = True
            _last_pg_check = now
            return True
        except Exception as e:
            _pg_available = False
            _last_pg_check = now
            raise RuntimeError(f"PostgreSQL database is unreachable: {e}")
            
    if _pg_available and (now - _last_pg_check) >= (_PG_RECHECK_AFTER):
        try:
            conn = psycopg2.connect(**PG_CONFIG)
            conn.close()
            _pg_available = True
            _last_pg_check = now
            return True
        except Exception as e:
            _pg_available = False
            _last_pg_check = now
            raise RuntimeError(f"PostgreSQL database is unreachable: {e}")
            
    if not _pg_available:
        raise RuntimeError("PostgreSQL database is unreachable.")
    return _pg_available


def wait_for_pg(max_attempts=15, delay=2):
    for attempt in range(max_attempts):
        try:
            if is_available():
                if attempt > 0:
                    print(f"[pg] PostgreSQL ready after {attempt} retries.")
                return True
        except RuntimeError:
            pass
        if attempt < max_attempts - 1:
            print(f"[pg] Waiting for PostgreSQL... (attempt {attempt+1}/{max_attempts})")
            time.sleep(delay)
    print("[pg] PostgreSQL did not become available in time.")
    return False


def get_connection():
    """Return a connection from the pool (reuses TCP connections)."""
    if not HAS_PSYCOPG2:
        raise RuntimeError("psycopg2 is not installed. Run: pip install psycopg2-binary")
    pool = _get_pool()
    try:
        conn = pool.getconn()
        return _PooledConnection(conn)
    except psycopg2.pool.PoolError:
        pass
    # Fallback: create a new direct connection if pool is exhausted
    last_exc = None
    for host in [PG_CONFIG["host"], "localhost", "127.0.0.1"]:
        try:
            cfg = PG_CONFIG.copy()
            cfg["host"] = host
            return psycopg2.connect(**cfg)
        except Exception as e:
            last_exc = e
            continue
    raise last_exc or RuntimeError("Could not connect to PostgreSQL on any host")


def get_health_status():
    status = {
        "available": HAS_PSYCOPG2,
        "connected": False,
        "error": None,
        "config": {k: (v if k != "password" else "********") for k, v in PG_CONFIG.items()},
        "timestamp": datetime.now().isoformat()
    }

    if not HAS_PSYCOPG2:
        status["error"] = "psycopg2-binary not installed"
        return status

    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                status["connected"] = True
        finally:
            conn.close()
    except Exception as e:
        status["error"] = str(e)

    return status


def init_live_tables(conn):
    """Create live_bdr_raw and live_rings_raw tables if they don't exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS live_bdr_raw (
                machine_name VARCHAR(255) PRIMARY KEY,
                content TEXT NOT NULL,
                downloaded_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS live_rings_raw (
                machine_name VARCHAR(255) PRIMARY KEY,
                content TEXT NOT NULL,
                downloaded_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)


BLE_FAILED_DDL = """
CREATE TABLE IF NOT EXISTS ble_failed_rings (
    id SERIAL PRIMARY KEY,
    serial_number TEXT NOT NULL,
    machine TEXT NOT NULL,
    slot INTEGER,
    ring_mac TEXT,
    ring_name TEXT,
    error TEXT,
    fail_count INTEGER,
    firmware_version TEXT,
    hardware_version TEXT,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    snapshot_at TIMESTAMPTZ,
    UNIQUE (serial_number, machine)
);
CREATE INDEX IF NOT EXISTS idx_ble_failed_active ON ble_failed_rings (is_active);
CREATE INDEX IF NOT EXISTS idx_ble_failed_machine ON ble_failed_rings (machine);
CREATE INDEX IF NOT EXISTS idx_ble_failed_last_seen ON ble_failed_rings (last_seen);
"""


def init_ble_failed_rings_table(conn):
    """Create the ble_failed_rings table and indexes if they don't exist."""
    with conn.cursor() as cur:
        cur.execute(BLE_FAILED_DDL)


def init_logs_table(conn):
    """Create machine_logs table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS machine_logs (
                id SERIAL PRIMARY KEY,
                machine_name VARCHAR(255) NOT NULL,
                machine_ip VARCHAR(45) NOT NULL DEFAULT '',
                fetch_time TIMESTAMP NOT NULL DEFAULT NOW(),
                file_name VARCHAR(255) NOT NULL,
                file_size BIGINT DEFAULT 0,
                storage_location TEXT NOT NULL,
                collection_status VARCHAR(50) NOT NULL DEFAULT 'success',
                error_message TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_machine_logs_fetch_time ON machine_logs(fetch_time)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_machine_logs_machine_name ON machine_logs(machine_name)")


def add_dashboard_indexes(conn):
    """Add performance indexes for dashboard queries."""
    with conn.cursor() as cur:
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_bdr_downloaded_at ON live_bdr_raw(downloaded_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_rings_downloaded_at ON live_rings_raw(downloaded_at)")
        except Exception:
            pass


def init_db():
    if not HAS_PSYCOPG2:
        print("[postgres_db] psycopg2 not available, skipping PostgreSQL init")
        return False
    try:
        conn = get_connection()
        try:
            init_live_tables(conn)
            add_dashboard_indexes(conn)
            init_logs_table(conn)
            init_archive_table(conn)
            init_ble_failed_rings_table(conn)
            try:
                from ring_status import init_ring_status_table
                init_ring_status_table(conn)
            except Exception as e:
                print(f"[postgres_db] ring_status init skipped: {e}")
            try:
                with conn.cursor() as cur:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            except Exception:
                pass
            conn.commit()
            print("[postgres_db] PostgreSQL schema initialized successfully")
            return True
        except Exception as e:
            conn.rollback()
            print(f"[postgres_db] Error initializing schema: {e}")
            return False
        finally:
            conn.close()
    except Exception as e:
        print(f"[postgres_db] Could not connect to PostgreSQL: {e}")
        return False


def _normalize_dir_path(config_key, subdir):
    config_path = Path(__file__).resolve().parent.parent / "machines.json"
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
        dest = config.get(config_key) or config.get("destination")
        if dest:
            p = Path(dest) / subdir
            if p.exists():
                return p
    project_root = Path(__file__).resolve().parent.parent
    fallback = project_root / "data" / subdir
    if fallback.exists():
        return fallback
    return None


def get_bdr_dir_pg():
    return _normalize_dir_path("destination_bdr", "bdr")


def get_rings_dir_pg():
    return _normalize_dir_path("destination_rings", "rings")


def _is_empty_json(path):
    if not path.exists():
        return True
    return path.stat().st_size == 0


def _is_fresh_file(path, max_age_seconds=86400):  # 24 hours instead of 5 minutes
    """Check if file was modified within max_age_seconds (default 24 hours)."""
    try:
        return path.exists() and (time.time() - path.stat().st_mtime) <= max_age_seconds
    except OSError:
        return False


def _safe_load_json(path):
    try:
        if not path.exists() or path.stat().st_size == 0:
            return None
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, PermissionError, OSError) as e:
        return None


def _has_slot_data(data):
    if not isinstance(data, dict) or len(data) == 0:
        return False
    if 'serial_number' in data or 'ring_name' in data or 'bdr_state' in data or 'bdr_data' in data:
        return True
    slots = data.get('slots')
    if isinstance(slots, dict) and len(slots) > 0:
        return _has_any_occupied_slots(data)
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(v.get('serial_number'), str) and v['serial_number'] not in ('--', 'N/A', ''):
            return True
    return False


def _trim_battery_history(data, max_entries=20):
    slots = data.get('slots') if isinstance(data.get('slots'), dict) else data
    for slot_key, slot_val in slots.items():
        if not isinstance(slot_val, dict):
            continue
        history = slot_val.get('bdr_battery_history')
        if isinstance(history, list) and len(history) > max_entries:
            slot_val['bdr_battery_history'] = history[-max_entries:]


# ── Live BDR + Rings ─────────────────────────────────────────────────


def get_live_bdr():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT machine_name, content, downloaded_at FROM live_bdr_raw WHERE downloaded_at > NOW() - INTERVAL '30 minutes' ORDER BY machine_name"
            )
            rows = cur.fetchall()

            result = {}
            for r in rows:
                mn = r["machine_name"]
                try:
                    content = json.loads(r["content"])
                    if isinstance(content, dict) and _has_slot_data(content):
                        content["_meta"] = {"downloaded_at": r["downloaded_at"].isoformat() if hasattr(r["downloaded_at"], 'isoformat') else str(r["downloaded_at"])}
                        result[mn] = content
                except (json.JSONDecodeError, TypeError):
                    continue

            return result
    finally:
        conn.close()


def get_live_bdr_machine(machine):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT content, downloaded_at FROM live_bdr_raw WHERE machine_name = %s AND downloaded_at > NOW() - INTERVAL '30 minutes'",
                (machine,)
            )
            row = cur.fetchone()
            if not row:
                return None
            try:
                content = json.loads(row["content"])
            except (json.JSONDecodeError, TypeError):
                return None
            if isinstance(content, dict) and _has_slot_data(content):
                content["_meta"] = {"downloaded_at": row["downloaded_at"].isoformat() if hasattr(row["downloaded_at"], 'isoformat') else str(row["downloaded_at"])}
                return content
            return None
    finally:
        conn.close()


def get_live_rings():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT machine_name, content, downloaded_at FROM live_rings_raw WHERE content IS NOT NULL AND downloaded_at > NOW() - INTERVAL '30 minutes' ORDER BY machine_name"
            )
            rows = cur.fetchall()

            result = {}
            for r in rows:
                mn = r["machine_name"]
                try:
                    parsed = json.loads(r["content"])
                    if isinstance(parsed, dict) and _has_slot_data(parsed):
                        parsed["_meta"] = {"downloaded_at": r["downloaded_at"].isoformat() if hasattr(r["downloaded_at"], 'isoformat') else str(r["downloaded_at"])}
                        result[mn] = parsed
                except (json.JSONDecodeError, TypeError):
                    continue

            return result
    finally:
        conn.close()


def get_live_rings_machine(machine):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT content, downloaded_at FROM live_rings_raw WHERE machine_name = %s AND content IS NOT NULL AND downloaded_at > NOW() - INTERVAL '30 minutes'",
                (machine,)
            )
            row = cur.fetchone()
            if not row:
                return None
            try:
                parsed = json.loads(row["content"])
            except (json.JSONDecodeError, TypeError):
                return None
            if isinstance(parsed, dict) and _has_slot_data(parsed):
                parsed["_meta"] = {"downloaded_at": row["downloaded_at"].isoformat() if hasattr(row["downloaded_at"], 'isoformat') else str(row["downloaded_at"])}
                return parsed
            return None
    finally:
        conn.close()


def import_bdr_json_to_pg(machine_name, json_path):
    """Parse BDR JSON file and write directly to live_bdr_raw."""
    data = _safe_load_json(json_path)
    if data is None or not _has_slot_data(data):
        return
    raw_content = json.dumps(data)
    pg_conn = None
    try:
        pg_conn = get_connection()
        with pg_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO live_bdr_raw (machine_name, content, downloaded_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (machine_name) DO UPDATE SET
                    content = EXCLUDED.content,
                    downloaded_at = NOW()
            """, (machine_name, raw_content))
        pg_conn.commit()
    except Exception as e:
        if pg_conn:
            pg_conn.rollback()
    finally:
        if pg_conn:
            pg_conn.close()


def import_rings_json_to_pg(machine_name, json_path):
    """Parse rings JSON file and write directly to live_rings_raw."""
    data = _safe_load_json(json_path)
    if data is None or not _has_slot_data(data):
        return
    if isinstance(data, dict) and "slots" in data and isinstance(data["slots"], dict):
        data = data["slots"]
    elif isinstance(data, dict) and "session_id" in data:
        data = {k: v for k, v in data.items() if k != "session_id"}
    raw_content = json.dumps(data)
    pg_conn = None
    try:
        pg_conn = get_connection()
        with pg_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO live_rings_raw (machine_name, content, downloaded_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (machine_name) DO UPDATE SET
                    content = EXCLUDED.content,
                    downloaded_at = NOW()
            """, (machine_name, raw_content))
        try:
            update_ble_failed_from_file(pg_conn, machine_name, data)
        except Exception as e:
            print(f"[postgres_db] ble_failed update failed for {machine_name}: {e}")
        pg_conn.commit()
    except Exception as e:
        if pg_conn:
            pg_conn.rollback()
    finally:
        if pg_conn:
            pg_conn.close()


# ── BLE Failed Rings ────────────────────────────────────────────────

_BLE_FAILED_ERROR_RE = re.compile(r"BLE failed\s+(\d+)x", re.IGNORECASE)


def _extract_ble_failed(machine, slots):
    """Return BLE-failed record dicts for slots whose error matches 'BLE failed Nx'."""
    out = []
    for slot_num, s in slots.items():
        if not isinstance(s, dict):
            continue
        err = s.get("error")
        if not isinstance(err, str):
            continue
        m = _BLE_FAILED_ERROR_RE.search(err)
        if not m:
            continue
        sn = (s.get("serial_number") or "").strip()
        if not sn or sn in ("--", "N/A"):
            continue
        out.append({
            "serial_number": sn,
            "machine": machine,
            "slot": int(slot_num) if str(slot_num).isdigit() else None,
            "ring_mac": s.get("ring_mac"),
            "ring_name": s.get("ring_name"),
            "error": err,
            "fail_count": int(m.group(1)),
            "firmware_version": s.get("firmware_version"),
            "hardware_version": s.get("hardware_version"),
            "snapshot_at": datetime.now(timezone.utc),
        })
    return out


def _occupied_serials(slots):
    """Set of non-empty serial numbers present in a machine's rings file."""
    seen = set()
    for s in slots.values():
        if not isinstance(s, dict):
            continue
        sn = (s.get("serial_number") or "").strip()
        if sn and sn not in ("--", "N/A"):
            seen.add(sn)
    return seen


def update_ble_failed_from_file(conn, machine_name, slots):
    """Upsert active BLE-failed ring records for one machine, then resolve any
    previously-active records whose serial is no longer BLE-failed (cleared,
    replaced, or removed from the file). Returns the number of active records."""
    if not isinstance(slots, dict) or not slots:
        return 0
    with conn.cursor() as cur:
        for rec in _extract_ble_failed(machine_name, slots):
            cur.execute("""
                INSERT INTO ble_failed_rings (
                    serial_number, machine, slot, ring_mac, ring_name, error,
                    fail_count, firmware_version, hardware_version,
                    first_seen, last_seen, resolved_at, is_active, snapshot_at
                ) VALUES (
                    %(serial_number)s, %(machine)s, %(slot)s, %(ring_mac)s, %(ring_name)s, %(error)s,
                    %(fail_count)s, %(firmware_version)s, %(hardware_version)s,
                    NOW(), NOW(), NULL, TRUE, %(snapshot_at)s
                )
                ON CONFLICT (serial_number, machine) DO UPDATE SET
                    slot             = EXCLUDED.slot,
                    ring_mac         = EXCLUDED.ring_mac,
                    ring_name        = EXCLUDED.ring_name,
                    error            = EXCLUDED.error,
                    fail_count       = EXCLUDED.fail_count,
                    firmware_version = EXCLUDED.firmware_version,
                    hardware_version = EXCLUDED.hardware_version,
                    last_seen        = NOW(),
                    resolved_at      = NULL,
                    is_active        = TRUE,
                    snapshot_at      = EXCLUDED.snapshot_at
                WHERE ble_failed_rings.is_active = FALSE
                   OR ble_failed_rings.last_seen < EXCLUDED.snapshot_at
            """, rec)

        active = [r["serial_number"] for r in _extract_ble_failed(machine_name, slots)]
        if active:
            cur.execute("""
                UPDATE ble_failed_rings
                SET resolved_at = NOW(), is_active = FALSE
                WHERE machine = %s AND is_active = TRUE
                  AND serial_number NOT IN %s
            """, (machine_name, tuple(active)))
        else:
            cur.execute("""
                UPDATE ble_failed_rings
                SET resolved_at = NOW(), is_active = FALSE
                WHERE machine = %s AND is_active = TRUE
            """, (machine_name,))

        cur.execute("SELECT COUNT(*) FROM ble_failed_rings WHERE machine = %s AND is_active = TRUE", (machine_name,))
        return cur.fetchone()[0]


def get_ble_failed_rings():
    """Return all currently-active BLE-failed ring records, newest first."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, serial_number, machine, slot, ring_mac, ring_name, error,
                       fail_count, firmware_version, hardware_version,
                       first_seen, last_seen, resolved_at, is_active
                FROM ble_failed_rings
                WHERE is_active = TRUE
                ORDER BY last_seen DESC, machine, slot
            """)
            return cur.fetchall()
    finally:
        conn.close()


def get_ble_failed_history(limit=50):
    """Return recent BLE-failed records (active + resolved), newest first."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, serial_number, machine, slot, ring_mac, ring_name, error,
                       fail_count, firmware_version, hardware_version,
                       first_seen, last_seen, resolved_at, is_active
                FROM ble_failed_rings
                ORDER BY last_seen DESC
                LIMIT %s
            """, (int(limit),))
            return cur.fetchall()
    finally:
        conn.close()


def get_ble_failed_fallback():
    """Derive the current BLE-failed rings from files when PG is unavailable.
    Returns {active: [...], history: []} using live ring JSON files."""
    active = []
    rings = get_live_rings_fallback()
    for machine, slots in rings.items():
        for rec in _extract_ble_failed(machine, slots):
            active.append({
                "serial_number": rec["serial_number"],
                "machine": rec["machine"],
                "slot": rec["slot"],
                "ring_mac": rec["ring_mac"],
                "ring_name": rec["ring_name"],
                "error": rec["error"],
                "fail_count": rec["fail_count"],
                "firmware_version": rec["firmware_version"],
                "hardware_version": rec["hardware_version"],
                "first_seen": None,
                "last_seen": None,
                "resolved_at": None,
                "is_active": True,
            })
    active.sort(key=lambda r: (r["machine"], r["slot"]))
    return {"active": active, "history": []}


def _has_any_occupied_slots(data):
    """Check if JSON data has any slot with a real serial number (not '--', 'N/A', '')."""
    if not isinstance(data, dict):
        return False
    slots = data.get('slots') if isinstance(data.get('slots'), dict) else data
    for slot_key, slot_val in slots.items():
        if not isinstance(slot_val, dict):
            continue
        sn = slot_val.get('serial_number', '')
        if isinstance(sn, str) and sn.strip() not in ('', '--', 'N/A'):
            return True
    return False


def _delete_bdr_machine(machine_name):
    """Remove a machine row from live_bdr_raw."""
    try:
        pg_conn = get_connection()
        try:
            with pg_conn.cursor() as cur:
                cur.execute("DELETE FROM live_bdr_raw WHERE machine_name = %s", (machine_name,))
            pg_conn.commit()
        finally:
            pg_conn.close()
    except Exception as e:
        print(f"[postgres_db] Error deleting BDR machine {machine_name}: {e}")


def _delete_rings_machine(machine_name):
    """Remove a machine row from live_rings_raw."""
    try:
        pg_conn = get_connection()
        try:
            with pg_conn.cursor() as cur:
                cur.execute("DELETE FROM live_rings_raw WHERE machine_name = %s", (machine_name,))
            pg_conn.commit()
        finally:
            pg_conn.close()
    except Exception as e:
        print(f"[postgres_db] Error deleting Rings machine {machine_name}: {e}")


def sync_machines_from_files():
    """Check JSON directories for changes and import directly to PostgreSQL.
    Uses a single connection for all operations."""

    if not is_available():
        return

    bdr_dir = get_bdr_dir_pg()
    rings_dir = get_rings_dir_pg()

    if not bdr_dir and not rings_dir:
        print("[postgres_db] No JSON directories found (BDR/Rings). Check machines.json paths.")
        return

    config_path = Path(__file__).resolve().parent.parent / "machines.json"
    if not config_path.exists():
        print(f"[postgres_db] machines.json not found at {config_path}")
        return
    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    pg_conn = None
    try:
        pg_conn = get_connection()
        config_names = [m["name"] for m in config.get("machines", [])]

        with pg_conn.cursor() as cur:
            # Remove stale machines not in config
            if config_names:
                names_tuple = tuple(config_names)
                cur.execute("DELETE FROM live_bdr_raw WHERE machine_name NOT IN %s", (names_tuple,))
                cur.execute("DELETE FROM live_rings_raw WHERE machine_name NOT IN %s", (names_tuple,))

            bdr_count = 0
            rings_count = 0
            bdr_deleted = 0
            rings_deleted = 0

            for machine in config.get("machines", []):
                name = machine["name"]
                bdr_path = (bdr_dir / f"{name}.json") if bdr_dir else None
                rings_path = (rings_dir / f"{name}.json") if rings_dir else None

                # BDR
                if bdr_path and bdr_path.exists() and not _is_empty_json(bdr_path):
                    data = _safe_load_json(bdr_path)
                    if data is not None and _has_any_occupied_slots(data):
                        raw = json.dumps(data)
                        cur.execute("""
                            INSERT INTO live_bdr_raw (machine_name, content, downloaded_at)
                            VALUES (%s, %s, NOW())
                            ON CONFLICT (machine_name) DO UPDATE SET
                                content = EXCLUDED.content,
                                downloaded_at = NOW()
                        """, (name, raw))
                        bdr_count += 1
                    else:
                        cur.execute("DELETE FROM live_bdr_raw WHERE machine_name = %s", (name,))
                        bdr_deleted += 1
                else:
                    cur.execute("DELETE FROM live_bdr_raw WHERE machine_name = %s", (name,))
                    bdr_deleted += 1

                # Rings
                if rings_path and rings_path.exists() and not _is_empty_json(rings_path):
                    data = _safe_load_json(rings_path)
                    if data is not None and _has_any_occupied_slots(data):
                        if isinstance(data, dict) and "slots" in data and isinstance(data["slots"], dict):
                            data = data["slots"]
                        elif isinstance(data, dict) and "session_id" in data:
                            data = {k: v for k, v in data.items() if k != "session_id"}
                        raw = json.dumps(data)
                        cur.execute("""
                            INSERT INTO live_rings_raw (machine_name, content, downloaded_at)
                            VALUES (%s, %s, NOW())
                            ON CONFLICT (machine_name) DO UPDATE SET
                                content = EXCLUDED.content,
                                downloaded_at = NOW()
                        """, (name, raw))
                        try:
                            update_ble_failed_from_file(pg_conn, name, data)
                        except Exception as e:
                            print(f"[postgres_db] ble_failed update failed for {name}: {e}")
                        rings_count += 1
                    else:
                        cur.execute("DELETE FROM live_rings_raw WHERE machine_name = %s", (name,))
                        rings_deleted += 1
                else:
                    cur.execute("DELETE FROM live_rings_raw WHERE machine_name = %s", (name,))
                    rings_deleted += 1

        pg_conn.commit()

        if bdr_count > 0 or bdr_deleted > 0:
            print(f"[postgres_db] BDR: synced {bdr_count}, removed {bdr_deleted}")
        if rings_count > 0 or rings_deleted > 0:
            print(f"[postgres_db] Rings: synced {rings_count}, removed {rings_deleted}")

    except Exception as e:
        if pg_conn:
            try:
                pg_conn.rollback()
            except Exception:
                pass
        print(f"[postgres_db] Error in sync_machines_from_files: {e}")
    finally:
        if pg_conn:
            try:
                pg_conn.close()
            except Exception:
                pass


def list_machines_pg():
    """List distinct machine names from live_bdr_raw and live_rings_raw in PG."""
    if not HAS_PSYCOPG2:
        return []
    pg_conn = get_connection()
    try:
        with pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT machine_name FROM live_bdr_raw
                UNION
                SELECT machine_name FROM live_rings_raw
                ORDER BY machine_name
            """)
            return [r["machine_name"] for r in cur.fetchall()]
    except Exception as e:
        print(f"[postgres_db] Error listing machines: {e}")
        return []
    finally:
        pg_conn.close()


# ── File-based fallback (when PostgreSQL is unavailable) ────────────

def _get_fallback_bdr_dir():
    project_root = Path(__file__).resolve().parent.parent
    bdr_dir = project_root / "DESTINATION" / "bdr"
    if bdr_dir.exists():
        return bdr_dir
    config_path = project_root / "machines.json"
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
        dest = config.get("destination_bdr") or config.get("destination")
        if dest:
            p = Path(dest) / "bdr"
            if p.exists():
                return p
    return None


def _get_fallback_rings_dir():
    project_root = Path(__file__).resolve().parent.parent
    rings_dir = project_root / "DESTINATION" / "rings"
    if rings_dir.exists():
        return rings_dir
    config_path = project_root / "machines.json"
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
        dest = config.get("destination_rings") or config.get("destination")
        if dest:
            p = Path(dest) / "rings"
            if p.exists():
                return p
    return None


def get_live_bdr_fallback():
    bdr_dir = _get_fallback_bdr_dir()
    if not bdr_dir:
        return {}
    result = {}
    for f in sorted(bdr_dir.glob("*.json"), key=lambda p: p.stem.lower()):
        if not _is_fresh_file(f):
            continue
        name = f.stem
        data = _safe_load_json(f)
        if data is not None and _has_slot_data(data):
            result[name] = data
    return result


def get_live_bdr_machine_fallback(machine):
    bdr_dir = _get_fallback_bdr_dir()
    if not bdr_dir:
        return None
    path = bdr_dir / f"{machine}.json"
    if not path.exists():
        path = bdr_dir / f"{machine.lower()}.json"
    if not path.exists():
        return None
    if not _is_fresh_file(path):
        return None
    data = _safe_load_json(path)
    if data is not None and _has_slot_data(data):
        return data
    return None


def get_live_rings_fallback():
    rings_dir = _get_fallback_rings_dir()
    if not rings_dir:
        return {}
    result = {}
    for f in sorted(rings_dir.glob("*.json"), key=lambda p: p.stem.lower()):
        if not _is_fresh_file(f):
            continue
        name = f.stem
        data = _safe_load_json(f)
        if data is not None and _has_slot_data(data):
            if isinstance(data, dict) and "slots" in data and isinstance(data["slots"], dict):
                result[name] = data["slots"]
            elif isinstance(data, dict) and "session_id" in data:
                result[name] = {k: v for k, v in data.items() if k != "session_id"}
            else:
                result[name] = data
    return result


def get_live_rings_machine_fallback(machine):
    rings_dir = _get_fallback_rings_dir()
    if not rings_dir:
        return None
    path = rings_dir / f"{machine}.json"
    if not path.exists():
        path = rings_dir / f"{machine.lower()}.json"
    if not path.exists():
        return None
    if not _is_fresh_file(path):
        return None
    data = _safe_load_json(path)
    if data is not None and _has_slot_data(data):
        if isinstance(data, dict) and "slots" in data and isinstance(data["slots"], dict):
            return data["slots"]
        elif isinstance(data, dict) and "session_id" in data:
            return {k: v for k, v in data.items() if k != "session_id"}
        return data
    return None


def list_machines_fallback():
    machines = set()
    for d in [_get_fallback_bdr_dir(), _get_fallback_rings_dir()]:
        if d:
            for f in d.glob("*.json"):
                machines.add(f.stem)
    return sorted(machines)


def save_log_metadata(machine_name, machine_ip, file_name, file_size, storage_location, collection_status='success', error_message=None):
    """Save log file metadata to the machine_logs table."""
    if not HAS_PSYCOPG2:
        return False
    try:
        pg_conn = get_connection()
        try:
            with pg_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO machine_logs (machine_name, machine_ip, fetch_time, file_name, file_size, storage_location, collection_status, error_message)
                    VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s)
                """, (machine_name, machine_ip, file_name, file_size, storage_location, collection_status, error_message))
            pg_conn.commit()
            return True
        except Exception as e:
            pg_conn.rollback()
            print(f"[postgres_db] Error saving log metadata: {e}")
            return False
        finally:
            pg_conn.close()
    except Exception as e:
        print(f"[postgres_db] Error saving log metadata (connection): {e}")
        return False

def init_archive_table(conn):
    """Create archive_entries table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS archive_entries (
                id SERIAL PRIMARY KEY,
                serial_number VARCHAR(255) NOT NULL,
                serial_lower VARCHAR(255) NOT NULL,
                machine VARCHAR(255),
                state VARCHAR(50),
                machine_avg_bdr REAL,
                bdr REAL,
                snapshots INTEGER,
                total_cycles INTEGER,
                completed_cycles INTEGER,
                start_time DOUBLE PRECISION,
                last_update DOUBLE PRECISION,
                saved_at VARCHAR(100),
                created_at TIMESTAMP DEFAULT NOW(),
                date VARCHAR(20),
                time VARCHAR(20),
                slot INTEGER,
                battery_current REAL,
                firmware_version VARCHAR(100),
                ring_mac VARCHAR(50),
                ring_name VARCHAR(100),
                avg_bdr DOUBLE PRECISION,
                avg_bdr_is_stale BOOLEAN,
                avg_bdr_is_estimated BOOLEAN,
                stored_avg_bdr DOUBLE PRECISION,
                inter_cycle_avg_bdr DOUBLE PRECISION,
                test_start DOUBLE PRECISION,
                phase VARCHAR(100),
                cycle INTEGER,
                completed_workouts INTEGER,
                file_path VARCHAR(500),
                UNIQUE(serial_number, machine, saved_at)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_archive_serial_lower ON archive_entries(serial_lower)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_archive_saved_at ON archive_entries(saved_at DESC)")

def ingest_archive_to_pg(record):
    """Insert a new archive record into PostgreSQL."""
    if not HAS_PSYCOPG2:
        return False
    try:
        pg_conn = get_connection()
        try:
            with pg_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO archive_entries (
                        serial_number, serial_lower, machine, state, machine_avg_bdr, bdr,
                        snapshots, total_cycles, completed_cycles, start_time, last_update, saved_at,
                        date, time, slot, battery_current, firmware_version, ring_mac, ring_name,
                        avg_bdr, avg_bdr_is_stale, avg_bdr_is_estimated, stored_avg_bdr,
                        inter_cycle_avg_bdr, test_start, phase, cycle, completed_workouts
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (serial_number, machine, saved_at) DO NOTHING
                """, (
                    record.get("serial_number"),
                    str(record.get("serial_number", "")).lower(),
                    record.get("machine"),
                    record.get("state"),
                    record.get("machine_avg_bdr") or record.get("avg_bdr"),
                    record.get("bdr"),
                    record.get("snapshots"),
                    record.get("total_cycles"),
                    record.get("completed_cycles"),
                    record.get("start_time"),
                    record.get("last_update"),
                    record.get("saved_at"),
                    record.get("date"),
                    record.get("time"),
                    record.get("slot"),
                    record.get("battery_current"),
                    record.get("firmware_version"),
                    record.get("ring_mac"),
                    record.get("ring_name"),
                    record.get("avg_bdr"),
                    record.get("avg_bdr_is_stale", False),
                    record.get("avg_bdr_is_estimated", False),
                    record.get("stored_avg_bdr"),
                    record.get("inter_cycle_avg_bdr"),
                    record.get("test_start"),
                    record.get("phase"),
                    record.get("cycle"),
                    record.get("completed_workouts"),
                ))
            pg_conn.commit()
            return True
        except Exception as e:
            pg_conn.rollback()
            print(f"[postgres_db] Error ingesting archive record: {e}")
            return False
        finally:
            pg_conn.close()
    except Exception as e:
        print(f"[postgres_db] Connection error ingesting archive: {e}")
        return False

def search_archive_in_pg(serial_keys):
    """
    Query PostgreSQL for the latest snapshot of each serial number per machine.
    Returns a dictionary grouped by serial_lower.
    """
    if not HAS_PSYCOPG2 or not serial_keys:
        return {}
    
    results_map = {key: [] for key in serial_keys}
    try:
        pg_conn = get_connection()
        try:
            with pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                query = """
                    SELECT serial_number, machine, state, machine_avg_bdr, bdr,
                           snapshots, total_cycles, completed_cycles, start_time,
                           last_update, saved_at, date, time, slot, battery_current,
                           firmware_version, ring_mac, ring_name, avg_bdr,
                           avg_bdr_is_stale, avg_bdr_is_estimated, stored_avg_bdr,
                           inter_cycle_avg_bdr, test_start, phase, cycle,
                           completed_workouts, file_path
                    FROM archive_entries
                    WHERE serial_lower = ANY(%s)
                    ORDER BY serial_lower, machine, saved_at DESC
                """
                cur.execute(query, (serial_keys,))
                rows = cur.fetchall()
                grouped_rows = {}
                for row in rows:
                    rec = dict(row)
                    if not rec: continue
                    s_lower = str(rec.get("serial_number", "")).lower()
                    machine = rec.get("machine", "")
                    combo_key = (s_lower, machine)
                    if combo_key not in grouped_rows:
                        grouped_rows[combo_key] = []
                    grouped_rows[combo_key].append(rec)
                
                for combo_key, recs in grouped_rows.items():
                    s_lower, machine = combo_key
                    
                    best_bdr_rec = None
                    for r in recs:
                        avg = r.get("avg_bdr")
                        if avg is not None and avg != 0.0:
                            best_bdr_rec = r
                            break
                            
                    for i, rec in enumerate(recs):
                        row_type = "latest" if i == 0 else "history"
                        
                        is_stale = rec.get("avg_bdr_is_stale", False) or rec.get("avg_bdr") is None or rec.get("avg_bdr") == 0.0
                        
                        final_avg = rec.get("avg_bdr")
                        final_est = rec.get("avg_bdr_is_estimated", False)
                        final_stored = rec.get("stored_avg_bdr")
                        final_inter = rec.get("inter_cycle_avg_bdr")
                        final_completed = rec.get("completed_cycles", 0)
                        final_workouts = rec.get("completed_workouts")
                        final_stale = rec.get("avg_bdr_is_stale", False)
                        
                        if is_stale and best_bdr_rec:
                            final_avg = best_bdr_rec.get("avg_bdr")
                            final_est = best_bdr_rec.get("avg_bdr_is_estimated", False)
                            final_stored = best_bdr_rec.get("stored_avg_bdr")
                            final_inter = best_bdr_rec.get("inter_cycle_avg_bdr")
                            final_completed = best_bdr_rec.get("completed_cycles", 0)
                            final_workouts = best_bdr_rec.get("completed_workouts")
                            final_stale = False
                            
                            if not str(rec.get("state", "")).strip():
                                hs = str(best_bdr_rec.get("state", ""))
                                if hs and "bdr" not in hs.lower() and hs.strip():
                                    rec["state"] = hs
                        
                        if s_lower in results_map:
                            results_map[s_lower].append({
                                "type": row_type,
                                "serial_number": rec.get("serial_number", ""),
                                "machine": machine,
                                "date": rec.get("date", ""),
                                "time": rec.get("time", ""),
                                "slot": rec.get("slot"),
                                "state": rec.get("state", ""),
                                "battery_current": rec.get("battery_current"),
                                "firmware_version": rec.get("firmware_version", ""),
                                "ring_mac": rec.get("ring_mac", ""),
                                "ring_name": rec.get("ring_name", ""),
                                "avg_bdr": final_avg,
                                "machine_avg_bdr": final_avg,
                                "avg_bdr_is_stale": final_stale,
                                "avg_bdr_is_estimated": final_est,
                                "stored_avg_bdr": final_stored,
                                "inter_cycle_avg_bdr": final_inter,
                                "test_start": rec.get("test_start"),
                                "phase": rec.get("phase"),
                                "cycle": rec.get("cycle"),
                                "snapshots": rec.get("snapshots", 1),
                                "total_cycles": rec.get("total_cycles", 0),
                                "completed_cycles": final_completed,
                                "completed_workouts": final_workouts,
                                "start_time": rec.get("start_time") or rec.get("test_start"),
                                "last_update": rec.get("saved_at", ""),
                                "saved_at": rec.get("saved_at", ""),
                                "file_path": rec.get("file_path", "")
                            })
            return results_map
        except Exception as e:
            print(f"[postgres_db] Error searching archive: {e}")
            return {}
        finally:
            pg_conn.close()
    except Exception as e:
        print(f"[postgres_db] Connection error searching archive: {e}")
        return {}
