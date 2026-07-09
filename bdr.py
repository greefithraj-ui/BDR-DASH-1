"""
BDR CLI - Control all BDR services (PostgreSQL, API, Frontend)

Usage:
  python bdr.py start      Start all services in background
  python bdr.py stop       Stop all services
  python bdr.py status     Show service status
  python bdr.py restart    Restart all services
  python bdr.py enable     Enable auto-start on system boot
  python bdr.py disable    Disable auto-start on system boot
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PID_FILE = ROOT / ".run_pids"

API_PORT = 8000
VITE_PORT = 3001
PG_PORT = 5432

TASK_NAME = "BDR-AutoStart"
PYTHON = sys.executable
BDR_SCRIPT = str(ROOT / "bdr.py")


# ─── ANSI Colors ───────────────────────────────────────────────────────────────

class C:
    R = "\033[0m"
    B = "\033[1m"
    D = "\033[2m"
    BLU = "\033[38;5;33m"
    CYN = "\033[38;5;44m"
    GRN = "\033[38;5;35m"
    RED = "\033[38;5;160m"
    YLW = "\033[38;5;214m"
    WHT = "\033[38;5;255m"
    GRY = "\033[38;5;240m"


def _c(code, text):
    return f"{code}{text}{C.R}"


# ─── Port Helpers ──────────────────────────────────────────────────────────────

def _get_pids_on_port(port):
    try:
        result = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True, timeout=5,
        )
        pids = []
        target = f":{port}"
        for line in result.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 5 and target in parts[1] and parts[3] == "LISTENING":
                try:
                    pids.append(int(parts[-1]))
                except ValueError:
                    pass
        return pids
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return []


def _find_pid_by_port(port):
    pids = _get_pids_on_port(port)
    return pids[0] if pids else None


def _kill_port(port):
    for pid in _get_pids_on_port(port):
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True, timeout=5,
                )
            else:
                os.kill(pid, signal.SIGTERM)
        except (OSError, ValueError, subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass


def _wait_for_port(port, timeout=45, label="service"):
    start = time.time()
    while time.time() - start < timeout:
        pid = _find_pid_by_port(port)
        if pid:
            return pid
        time.sleep(0.5)
    return None


# ─── PostgreSQL Helpers ────────────────────────────────────────────────────────

def _kill_postgres_processes():
    if os.name != "nt":
        return
    pgdata_pattern = str(ROOT / "pgdata").replace("\\", "/")
    try:
        out = subprocess.check_output(
            'wmic process where "name=\'postgres.exe\'" get processid,commandline /format:csv',
            shell=True, text=True, timeout=5,
        )
        import csv
        import io
        reader = csv.reader(io.StringIO(out))
        for row in reader:
            if len(row) >= 3 and row[0] not in ("Node", ""):
                try:
                    cmdline = row[1]
                    pid = int(row[2])
                    if pgdata_pattern in cmdline:
                        subprocess.run(
                            ["taskkill", "/F", "/PID", str(pid)],
                            capture_output=True, timeout=5,
                        )
                except (ValueError, IndexError):
                    pass
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass


def _is_pg_ready():
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="127.0.0.1", port=5432,
            dbname="postgres", user="postgres",
            password="postgres", connect_timeout=2,
        )
        conn.close()
        return True
    except Exception:
        return False


def _pg_ensure():
    pg_bin = "C:\\Program Files\\PostgreSQL\\17\\bin"
    pg_ctl = os.path.join(pg_bin, "pg_ctl.exe")
    pgdata = ROOT / "pgdata"

    if not os.path.exists(pg_ctl):
        print(f"  [!] pg_ctl not found at {pg_ctl}")
        return False
    if not pgdata.exists():
        print(f"  [!] Data directory not found at {pgdata}")
        return False

    existing_pid = _find_pid_by_port(5432)
    if existing_pid:
        if _is_pg_ready():
            print(f"  [+] PostgreSQL already running (PID {existing_pid})")
            return True
        _kill_postgres_processes()
        time.sleep(1)

    _kill_postgres_processes()
    time.sleep(1)

    pid_file = pgdata / "postmaster.pid"
    if pid_file.exists():
        try:
            pid_file.unlink()
        except OSError:
            pass

    print(f"  [~] Starting PostgreSQL...")
    try:
        subprocess.Popen(
            [pg_ctl, "start", "-D", str(pgdata),
             "-o", "-c logging_collector=on -c log_directory=pg_log",
             "-t", "60"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        print(f"  [!!] pg_ctl start error: {e}")
        return False

    start = time.time()
    timeout = 120
    port_found = False
    while time.time() - start < timeout:
        pid = _find_pid_by_port(5432)
        if pid:
            if not port_found:
                port_found = True
            if _is_pg_ready():
                print(f"  [+] PostgreSQL started (port 5432, PID {pid})")
                _pg_ensure_database()
                return True
        time.sleep(1)

    print(f"  [!] PostgreSQL failed to start within {timeout}s")
    return False


def _pg_ensure_database():
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="127.0.0.1", port=5432,
            dbname="postgres", user="postgres",
            password="postgres", connect_timeout=3,
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'bdr_dashboard'")
        exists = cur.fetchone() is not None
        if not exists:
            cur.execute("CREATE DATABASE bdr_dashboard")
            print(f"  [+] Created database 'bdr_dashboard'")
        conn.close()
        return True
    except Exception:
        return False


def _pg_stop():
    if os.name != "nt":
        return
    pid = _find_pid_by_port(5432)
    if not pid:
        return
    pgdata = ROOT / "pgdata"
    pg_bin = "C:\\Program Files\\PostgreSQL\\17\\bin"
    pg_ctl = os.path.join(pg_bin, "pg_ctl.exe")
    if not os.path.exists(pg_ctl) or not pgdata.exists():
        return

    print(f"  [+] Stopping PostgreSQL... (PID {pid})")
    try:
        subprocess.run(
            [pg_ctl, "stop", "-D", str(pgdata), "-m", "fast"],
            capture_output=True, text=True, timeout=30,
        )
        time.sleep(2)
        if not _find_pid_by_port(5432):
            return
    except (subprocess.TimeoutExpired, Exception):
        pass

    print(f"      Force killing PostgreSQL...")
    _kill_postgres_processes()


# ─── PID Tracking ──────────────────────────────────────────────────────────────

def _read_pids():
    if PID_FILE.exists():
        try:
            return json.loads(PID_FILE.read_text())
        except (json.JSONDecodeError, KeyError):
            pass
    return {}


def _write_pids(pids):
    PID_FILE.write_text(json.dumps(pids, indent=2))


# ─── Old Data ────────────────────────────────────────────────────────────────────

def cmd_old_data(serial):
    print()
    print(f"  {'='*50}")
    print(f"  {_c(C.B + C.BLU, 'Searching archive for serial:')} {serial}")
    print(f"  {'='*50}")
    print()

    import json
    from pathlib import Path

    # Try API first (faster if index is built)
    api_pid = _find_pid_by_port(API_PORT)
    if api_pid:
        import urllib.request
        import urllib.error
        try:
            url = f"http://127.0.0.1:{API_PORT}/api/old-data/search/{urllib.parse.quote(serial, safe='')}"
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            if data.get("ok"):
                results = data.get("results", [])
                total = data.get("count", 0)
                print(f"  [~] Via API ({'indexed' if data.get('indexed') else 'direct scan'})")
                print()
                if not results:
                    print(f"  {_c(C.YLW, 'No matches found.')}")
                    print()
                    return 0
                _print_old_data_results(results, total)
                return 0
        except Exception as e:
            print(f"  [~] API search failed ({e}), falling back to direct scan...")
            print()

    # Direct scan fallback
    root = Path(__file__).resolve().parent
    machines_json = root / "machines.json"
    if not machines_json.exists():
        print(f"  [!] machines.json not found")
        return 1

    with machines_json.open("r") as f:
        config = json.load(f)
    destination = config.get("destination", "")
    if not destination:
        print(f"  [!] No destination configured")
        return 1

    archive_root = Path(destination) / "archive"
    if not archive_root.is_dir():
        print(f"  [!] Archive directory not found at {archive_root}")
        return 1

    serial_lower = serial.lower()
    all_files = list(archive_root.rglob("*.json"))
    total = len(all_files)
    print(f"  [~] Scanning {total} archive files (this may take a while)...")
    print()

    results = []
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _calc_avg_bdr(slot_data):
        bdr_data = slot_data.get("bdr_data")
        if isinstance(bdr_data, dict) and bdr_data.get("avg_bdr") is not None:
            return bdr_data["avg_bdr"]
        bdr_state = slot_data.get("bdr_state") or {}
        cycles = bdr_state.get("completed_cycles") or []
        if cycles:
            vals = [c.get("bdr", 0) for c in cycles if c.get("bdr") is not None]
            return round(sum(vals) / len(vals), 2) if vals else None
        return None

    def _scan_chunk(files):
        chunk_results = []
        for snap_file in files:
            if snap_file.suffix != ".json":
                continue
            try:
                data = json.loads(snap_file.read_text("utf-8", errors="replace"))
                for slot_key, slot_data in data.get("slots", {}).items():
                    sn = slot_data.get("serial_number", "").strip()
                    if serial_lower in sn.lower():
                        bdr_data = slot_data.get("bdr_data") or {}
                        bdr_state = slot_data.get("bdr_state") or {}
                        completed_cycles = bdr_state.get("completed_cycles") or []
                        bdr_cycles = bdr_data.get("cycles") or []
                        chunk_results.append({
                            "machine": snap_file.parent.parent.name,
                            "date": snap_file.parent.name,
                            "time": snap_file.stem,
                            "slot": int(slot_key),
                            "saved_at": data.get("saved_at", ""),
                            "serial_number": sn,
                            "state": slot_data.get("state", ""),
                            "battery_current": slot_data.get("battery_current"),
                            "firmware_version": slot_data.get("firmware_version", ""),
                            "ring_mac": slot_data.get("ring_mac", ""),
                            "ring_name": slot_data.get("ring_name", ""),
                            "avg_bdr": _calc_avg_bdr(slot_data),
                            "stored_avg_bdr": bdr_data.get("stored_avg_bdr"),
                            "inter_cycle_avg_bdr": bdr_data.get("inter_cycle_avg_bdr"),
                            "test_start": bdr_data.get("test_start"),
                            "phase": bdr_state.get("phase") or bdr_data.get("phase_at_finalize"),
                            "cycle": bdr_state.get("cycle") or bdr_data.get("final_cycle"),
                            "total_cycles": max(len(completed_cycles), len(bdr_cycles)),
                        })
            except (json.JSONDecodeError, KeyError, ValueError):
                pass
        return chunk_results

    n_workers = os.cpu_count() or 4
    chunk_size = max(1, total // n_workers)
    chunks = [all_files[i:i + chunk_size] for i in range(0, total, chunk_size)]
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futures = [pool.submit(_scan_chunk, chunk) for chunk in chunks]
        done = 0
        for f in as_completed(futures):
            results.extend(f.result())
            done += 1
            if done % 2 == 0:
                print(f"       [{done}/{len(chunks)} chunks complete, {len(results)} matches so far...")

    print()
    if not results:
        print(f"  {_c(C.YLW, 'No matches found.')}")
        print()
        return 0

    _print_old_data_results(results, len(results))
    return 0


def _print_old_data_results(results, total):
    from collections import defaultdict
    # Group by machine with aggregation (reference CLI method)
    by_machine = {}
    machine_agg = defaultdict(lambda: {
        "snapshots": 0, "avg_bdr_vals": [],
        "states": set(), "phases": set(), "cycles": set(),
    })
    for r in results:
        mach = r.get("machine", "")
        agg = machine_agg[mach]
        agg["snapshots"] += 1
        if r.get("avg_bdr") is not None:
            agg["avg_bdr_vals"].append(r["avg_bdr"])
        if r.get("state"):
            agg["states"].add(r["state"])
        if r.get("phase"):
            agg["phases"].add(r["phase"])
        if r.get("cycle") is not None:
            agg["cycles"].add(r["cycle"])

        existing = by_machine.get(mach)
        if not existing or r.get("saved_at", "") > existing.get("saved_at", ""):
            by_machine[mach] = r

    # Only return the latest machine (most recent saved_at)
    if by_machine:
        latest = max(by_machine.values(), key=lambda x: x.get("saved_at", ""))
        latest_mach = latest["machine"]
        latest_agg = machine_agg[latest_mach]
        latest["snapshots"] = latest_agg["snapshots"]
        latest["machine_avg_bdr"] = (
            round(sum(latest_agg["avg_bdr_vals"]) / len(latest_agg["avg_bdr_vals"]), 2)
            if latest_agg["avg_bdr_vals"] else None
        )

        print(f"  {_c(C.GRN, f'Found {total} match(es) on {len(by_machine)} machine(s) — latest: {latest_mach}')}")
        print()
        header = f"  {'MACHINE':<12} {'DATE':<12} {'TIME':<10} {'SLOT':<5} {'STATE':<18} {'PHASE':<14} {'CYCLE':<6} {'BATT':<6} {'BDR':<8} {'INTER':<8} {'CYCLES':<6} {'SNAP':<5} {'SERIAL'}"
        print(f"  {_c(C.D, header)}")
        print(f"  {_c(C.D, '-' * 135)}")
        r = latest
        batt = str(r["battery_current"]) if r.get("battery_current") is not None else "--"
        bdr_val = r.get("avg_bdr")
        bdr = f"{bdr_val:.2f}" if bdr_val is not None else "--"
        bdr_all_vals = latest_agg["avg_bdr_vals"]
        inter_val = r.get("inter_cycle_avg_bdr")
        inter = f"{inter_val:.2f}" if inter_val is not None else "--"
        cyc_val = r.get("total_cycles")
        cyc = str(cyc_val) if cyc_val is not None else "--"
        snap = str(latest_agg["snapshots"])
        phase = r.get("phase") or "--"
        cycle = str(r.get("cycle")) if r.get("cycle") is not None else "--"
        print(f"  {r['machine']:<12} {r['date']:<12} {r['time']:<10} {r['slot']:<5} {r['state']:<18} {phase:<14} {cycle:<6} {batt:<6} {bdr:<8} {inter:<8} {cyc:<6} {snap:<5} {r['serial_number']}")
    print()


def _is_running(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, PermissionError):
        return False


def _kill_pid(pid):
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, timeout=5,
            )
        else:
            os.kill(pid, signal.SIGTERM)
    except (OSError, subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass


# ─── Status ────────────────────────────────────────────────────────────────────

def _get_status():
    pids = _read_pids()
    pg_alive = _find_pid_by_port(PG_PORT) is not None
    api_alive = _is_running(pids.get("api"))
    vite_alive = _is_running(pids.get("vite"))

    if not api_alive:
        pid = _find_pid_by_port(API_PORT)
        if pid:
            api_alive = True
            pids["api"] = pid
            _write_pids(pids)

    if not vite_alive:
        pid = _find_pid_by_port(VITE_PORT)
        if pid:
            vite_alive = True
            pids["vite"] = pid
            _write_pids(pids)

    return pg_alive, api_alive, vite_alive, pids


def cmd_status():
    pg_alive, api_alive, vite_alive, pids = _get_status()

    def _line(name, port, alive, pid):
        dot = _c(C.GRN, ">>") if alive else _c(C.RED, "..")
        lbl = _c(C.GRN, "RUNNING") if alive else _c(C.RED, "STOPPED")
        pid_str = _c(C.GRY, f"  (PID {pid})") if alive and pid else ""
        return f"  {dot}  {name:<13}  port {port:<6}  {lbl}{pid_str}"

    auto = _is_auto_start_enabled()

    print()
    print(f"  {'='*58}")
    print(f"  {_c(C.B + C.BLU, 'BDR DASHBOARD')} - Service Status")
    print(f"  {'='*58}")
    print()
    print(f"  {'SERVICE':<16}  {'PORT':<9}  STATUS")
    print(f"  {'-'*44}")
    print(_line("PostgreSQL", PG_PORT, pg_alive, _find_pid_by_port(PG_PORT)))
    print(_line("API Server", API_PORT, api_alive, pids.get("api")))
    print(_line("Frontend", VITE_PORT, vite_alive, pids.get("vite")))
    print(f"  {'-'*44}")
    print()
    if api_alive and vite_alive:
        print(f"  Dashboard: {_c(C.CYN, f'http://localhost:{VITE_PORT}')}")
    print(f"  Auto-start: {_c(C.GRN, 'ENABLED') if auto else _c(C.RED, 'DISABLED')}")
    print()

    return 0 if api_alive and vite_alive else 1


# ─── Start ─────────────────────────────────────────────────────────────────────

def cmd_start():
    print()
    print(f"  {'='*50}")
    print(f"  {_c(C.B + C.BLU, 'Starting all BDR services...')}")
    print(f"  {'='*50}")
    print()

    pg_alive, api_alive, vite_alive, _ = _get_status()

    # 1. PostgreSQL
    if not _find_pid_by_port(PG_PORT):
        pg_ok = _pg_ensure()
        if pg_ok:
            print(f"  [+] PostgreSQL ready")
        else:
            print(f"  [-] PostgreSQL not available — API will use file fallback")
    else:
        print(f"  [+] PostgreSQL already running")

    # 2. API Server
    if not api_alive:
        print(f"  [~] Starting API server...")
        _kill_port(API_PORT)

        # Clean up stale PID files so bg_api_loop doesn't think another instance is running
        for pid_file in [ROOT / "data" / "api_bg.pid", ROOT / ".run_pids"]:
            try:
                if pid_file.exists():
                    pid_file.unlink()
            except OSError:
                pass

        log_file = ROOT / "data" / "api_bg.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text("")  # truncate for fresh start
        log_handle = open(log_file, "a", encoding="utf-8")

        subprocess_env = {**os.environ, "AQC_PASSWORD": os.environ.get("AQC_PASSWORD", "1234")}
        subprocess.Popen(
            [sys.executable, str(ROOT / "data" / "main.py"), "--bg-api"],
            cwd=ROOT,
            stdout=log_handle, stderr=subprocess.STDOUT,
            env=subprocess_env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        log_handle.close()

        api_pid = _wait_for_port(API_PORT, timeout=45, label="API")
        if api_pid:
            print(f"  [+] API server ready on {_c(C.CYN, f'http://localhost:{API_PORT}')}")
        else:
            print(f"  [!!] API server failed to start — check data/api_bg.log")
    else:
        api_pid = _find_pid_by_port(API_PORT)
        print(f"  [+] API server already running (PID {api_pid})")

    # 3. Frontend (static server from dist/, no Vite file watcher)
    if not vite_alive:
        print(f"  [~] Starting Frontend...")
        _kill_port(VITE_PORT)

        subprocess.Popen(
            ["node", "serve-dist.js"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

        vite_pid = _wait_for_port(VITE_PORT, timeout=30, label="Frontend")
        if vite_pid:
            print(f"  [+] Frontend ready on {_c(C.CYN, f'http://localhost:{VITE_PORT}')}")
        else:
            print(f"  [!!] Frontend failed to start")
    else:
        vite_pid = _find_pid_by_port(VITE_PORT)
        print(f"  [+] Frontend already running (PID {vite_pid})")

    # Save PIDs
    _write_pids({
        "api": _find_pid_by_port(API_PORT),
        "vite": _find_pid_by_port(VITE_PORT),
    })

    print()
    if _find_pid_by_port(API_PORT) and _find_pid_by_port(VITE_PORT):
        print(f"  {_c(C.B + C.GRN, 'All services started successfully!')}")
        print(f"  Dashboard: {_c(C.CYN, f'http://localhost:{VITE_PORT}')}")
    else:
        print(f"  {_c(C.B + C.YLW, 'Startup partially failed — check logs above.')}")
    print()

    return 0


# ─── Stop ──────────────────────────────────────────────────────────────────────

def cmd_stop():
    print()
    print(f"  {'='*50}")
    print(f"  {_c(C.B + C.BLU, 'Stopping all BDR services...')}")
    print(f"  {'='*50}")
    print()

    _, api_alive, vite_alive, pids = _get_status()

    if vite_alive and pids.get("vite"):
        print(f"  [+] Stopping Frontend... (PID {pids['vite']})")
        _kill_pid(pids["vite"])

    if api_alive and pids.get("api"):
        print(f"  [+] Stopping API server... (PID {pids['api']})")
        _kill_pid(pids["api"])

    _kill_port(API_PORT)
    _kill_port(VITE_PORT)

    _pg_stop()

    if PID_FILE.exists():
        PID_FILE.unlink()

    if not api_alive and not vite_alive:
        print(f"  [--] No services were running")
    else:
        print(f"  {_c(C.B + C.GRN, 'All services stopped')}")
    print()

    return 0


# ─── Restart ───────────────────────────────────────────────────────────────────

def cmd_restart():
    cmd_stop()
    time.sleep(2)
    cmd_start()
    return 0


# ─── Auto-Start (Windows Task Scheduler) ───────────────────────────────────────

def _get_task_command():
    return f'"{PYTHON}" "{BDR_SCRIPT}" start'


def _is_auto_start_enabled():
    if os.name != "nt":
        return False
    try:
        subprocess.run(
            ["schtasks", "/Query", "/TN", TASK_NAME],
            capture_output=True, timeout=5, check=True,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def cmd_enable():
    if os.name != "nt":
        print("  [!] Auto-start is only supported on Windows")
        return 1

    if _is_auto_start_enabled():
        print(f"  [+] Auto-start already enabled (task '{TASK_NAME}' exists)")
        return 0

    task_command = _get_task_command()

    # Try with highest privileges first, then fall back
    attempts = [
        ["schtasks", "/Create", "/SC", "ONSTART",
         "/TN", TASK_NAME, "/TR", task_command,
         "/RL", "HIGHEST", "/F"],
        ["schtasks", "/Create", "/SC", "ONSTART",
         "/TN", TASK_NAME, "/TR", task_command, "/F"],
    ]

    last_error = ""
    for attempt_cmd in attempts:
        try:
            result = subprocess.run(
                attempt_cmd,
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                print(f"  {_c(C.GRN, 'Auto-start ENABLED')}")
                print(f"      Task '{TASK_NAME}' will run '{task_command}'")
                print(f"      at every system startup.")
                print(f"      {'(requires admin privileges)' if '/RL' in attempt_cmd else '(runs at user logon)'}")
                print()
                return 0
            last_error = result.stderr.strip() or result.stdout.strip()
        except subprocess.TimeoutExpired:
            last_error = "timed out"

    print(f"  [!] Failed to create scheduled task:")
    print(f"      {last_error}")
    print(f"      Run the terminal as Administrator and try again.")
    print()
    return 1


def cmd_disable():
    if os.name != "nt":
        print("  [!] Auto-start is only supported on Windows")
        return 1

    if not _is_auto_start_enabled():
        print(f"  [--] Auto-start was not enabled")
        return 0

    try:
        subprocess.run(
            ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
            capture_output=True, text=True, timeout=10, check=True,
        )
        print(f"  {_c(C.RED, 'Auto-start DISABLED')}")
        print(f"      Task '{TASK_NAME}' removed.")
        print()
        return 0
    except subprocess.CalledProcessError as e:
        print(f"  [!!] Failed to delete scheduled task:")
        print(f"      {e.stderr.strip() or e.stdout.strip()}")
        return 1
    except subprocess.TimeoutExpired:
        print(f"  [!!] schtasks timed out")
        return 1


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BDR CLI — Control all BDR services, search archive data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python bdr.py start              Start all services in background\n"
            "  python bdr.py stop               Stop all services\n"
            "  python bdr.py status             Show service status\n"
            "  python bdr.py restart            Restart all services\n"
            "  python bdr.py enable             Enable auto-start on system boot\n"
            "  python bdr.py disable            Disable auto-start on system boot\n"
            "  python bdr.py old-data <serial>  Search archived data by serial number"
        ),
    )
    parser.add_argument(
        "command",
        choices=["start", "stop", "status", "restart", "enable", "disable", "old-data"],
        help="Command to execute",
    )
    parser.add_argument(
        "serial",
        nargs="?",
        default=None,
        help="Serial number to search (required for old-data command)",
    )
    args = parser.parse_args()

    if args.command == "old-data":
        if not args.serial:
            parser.error("old-data requires a serial number argument")
        return cmd_old_data(args.serial)

    commands = {
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "restart": cmd_restart,
        "enable": cmd_enable,
        "disable": cmd_disable,
    }

    return commands[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
