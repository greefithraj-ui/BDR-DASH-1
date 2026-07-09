import csv
import io
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PID_FILE = ROOT / ".run_pids"
API_PORT = 8000
VITE_PORT = 3001

# -- psycopg2 availability -----------------------------------------------------
try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    psycopg2 = None  # noqa: F811
    HAS_PSYCOPG2 = False

# -- ANSI Colors ----------------------------------------------------------------

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

def _clear():
    os.system("cls" if os.name == "nt" else "clear")

# -- Port Helpers ---------------------------------------------------------------

def _get_pids_on_port(port):
    """Return list of PIDs listening on given port."""
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
    time.sleep(0.5)

def _find_pid_by_port(port):
    pids = _get_pids_on_port(port)
    return pids[0] if pids else None

def _wait_for_port(port, timeout=45, label="service"):
    start = time.time()
    while time.time() - start < timeout:
        pid = _find_pid_by_port(port)
        if pid:
            return pid
        elapsed = int(time.time() - start)
        if elapsed > 0 and elapsed % 5 == 0:
            print(f"       [~] Waiting for {label}... {elapsed}s")
        time.sleep(0.5)
    elapsed = int(time.time() - start)
    print(f"       [~] Waiting for {label}... {elapsed}s (timeout)")
    return None

# -- PostgreSQL Health Check ----------------------------------------------------

def _kill_postgres_processes():
    """Kill any orphaned postgres.exe processes from our pgdata dir.

    Uses wmic + csv to check the command line of each postgres.exe so we
    only touch processes that reference our pgdata directory.
    """
    if os.name != "nt":
        return
    # wmic outputs paths with forward slashes, match that
    pgdata_pattern = str(ROOT / "pgdata").replace("\\", "/")
    try:
        out = subprocess.check_output(
            "wmic process where \"name='postgres.exe'\" get processid,commandline /format:csv",
            shell=True, text=True, timeout=5,
        )
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
    """Check if PostgreSQL is accepting connections.

    Connects to the maintenance 'postgres' database (always exists) so
    this function works even before 'bdr_dashboard' has been created.
    """
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

def _pg_cancel_stuck():
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="127.0.0.1", port=5432,
            dbname="bdr_dashboard", user="postgres",
            password="postgres", connect_timeout=3,
        )
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("""
            SELECT pg_cancel_backend(pid)
            FROM pg_stat_activity
            WHERE pid != pg_backend_pid()
              AND state = 'active'
              AND query NOT LIKE '%pg_stat_activity%'
              AND query NOT LIKE '%pg_cancel_backend%'
        """)
        cancelled = cur.rowcount
        cur.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE pid != pg_backend_pid()
              AND datname = current_database()
              AND state = 'idle'
              AND state_change < now() - interval '5 seconds'
        """)
        terminated = cur.rowcount
        conn.close()
        return cancelled, terminated
    except Exception:
        return -1, -1

def _pg_ensure():
    """Ensure PostgreSQL is running and bdr_dashboard database exists."""
    pg_bin = "C:\\Program Files\\PostgreSQL\\17\\bin"
    pg_ctl = os.path.join(pg_bin, "pg_ctl.exe")
    pgdata = ROOT / "pgdata"

    if not os.path.exists(pg_ctl):
        print(f"       [!] pg_ctl not found at {pg_ctl}")
        return False
    if not pgdata.exists():
        print(f"       [!] Data directory not found at {pgdata}")
        return False

    # -- Check if PG is already listening on port 5432 -------------------------
    existing_pid = _find_pid_by_port(5432)
    if existing_pid:
        print(f"       [+] PostgreSQL already running (PID {existing_pid})")
        print(f"       [..] Waiting for it to accept connections...")
        start = time.time()
        timeout = 30
        while time.time() - start < timeout:
            if _is_pg_ready():
                print(f"       [+] PostgreSQL accepting connections")
                return _pg_ensure_database()
            time.sleep(1)
        elapsed = int(time.time() - start)
        print(f"       [!] PostgreSQL PID {existing_pid} did not accept connections within {elapsed}s")
        print(f"       [..] Will try to start fresh instead...")
        _kill_postgres_processes()
        time.sleep(1)
        # Fall through to fresh start below

    # -- Kill orphaned postgres processes and stale files ----------------------
    _kill_postgres_processes()
    time.sleep(1)

    pid_file = pgdata / "postmaster.pid"
    if pid_file.exists():
        try:
            pid_file.unlink()
            print(f"       [..] Removed stale postmaster.pid")
        except OSError:
            pass

    old_log = pgdata / "pg.log"
    if old_log.exists():
        try:
            old_log.unlink()
        except OSError:
            pass

    # -- Start PostgreSQL ------------------------------------------------------
    print(f"       [..] Starting PostgreSQL...")
    print(f"       [..] Using logging_collector (logs in pgdata/pg_log/)")
    print(f"       [..] pg_ctl timeout: 60s, poll timeout: 120s")

    try:
        proc = subprocess.Popen(
            [pg_ctl, "start", "-D", str(pgdata),
             "-o", "-c logging_collector=on -c log_directory=pg_log",
             "-t", "60"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        try:
            stdout, stderr = proc.communicate(timeout=10)
            if proc.returncode != 0:
                err = (stderr.strip() or stdout.strip())
                print(f"       [!] pg_ctl start failed: {err[:200]}")
                _pg_dump_log(pgdata)
                return False
        except subprocess.TimeoutExpired:
            pass
    except Exception as e:
        print(f"       [!!] pg_ctl start error: {e}")
        _pg_dump_log(pgdata)
        return False

    # -- Wait for port to open and verify queries work -------------------------
    print(f"       [..] Waiting for PostgreSQL to accept connections...")
    start = time.time()
    timeout = 120
    port_found = False
    while time.time() - start < timeout:
        pid = _find_pid_by_port(5432)
        if pid:
            if not port_found:
                port_found = True
                print(f"       [..] Port 5432 open (PID {pid}), checking query readiness...")
            if _is_pg_ready():
                print(f"       [+] PostgreSQL started (port 5432, PID {pid})")
                return _pg_ensure_database()
        elapsed = int(time.time() - start)
        if elapsed > 0 and elapsed % 10 == 0:
            status = f"port open, waiting for queries" if port_found else "waiting for port"
            print(f"           still waiting... {elapsed}s ({status})")
        time.sleep(1)

    # -- Diagnostics on failure ------------------------------------------------
    print(f"       [!] PostgreSQL failed to start within {timeout}s")
    _pg_dump_log(pgdata)
    return False

def _pg_ensure_database():
    """Create bdr_dashboard database if it doesn't exist."""
    if not HAS_PSYCOPG2:
        return False
    for attempt in range(5):
        try:
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
                print(f"       [+] Created database 'bdr_dashboard'")
            conn.close()
            return True
        except Exception as e:
            if attempt < 4:
                print(f"       [..] Database connect attempt {attempt+1} failed, retrying... ({e})")
                time.sleep(2)
            else:
                print(f"       [!] Database setup failed after 5 attempts: {e}")
    return False

def _pg_stop():
    """Stop PostgreSQL cleanly (only if it is using our pgdata directory)."""
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

    # Verify the process on port 5432 is actually our PostgreSQL
    # (wmic outputs paths with forward slashes, use csv module to parse)
    try:
        out = subprocess.check_output(
            "wmic process where \"name='postgres.exe'\" get processid,commandline /format:csv",
            shell=True, text=True, timeout=5,
        )
        our_pgdata = str(pgdata).replace("\\", "/")
        found = False
        reader = csv.reader(io.StringIO(out))
        for row in reader:
            if len(row) >= 3 and row[0] not in ("Node", ""):
                try:
                    if int(row[2]) == pid and our_pgdata in row[1]:
                        found = True
                        break
                except (ValueError, IndexError):
                    pass
        if not found:
            return
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass

    print(f"  [+] Stopping PostgreSQL... {_c(C.GRY, f'(PID {pid})')}")
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

    print(f"       [!] pg_ctl stop failed, force killing...")
    _kill_postgres_processes()
    time.sleep(1)

def _pg_dump_log(pgdata):
    """Print recent fatal/error lines from pg.log or pg_log/*.log."""
    log_dir = pgdata / "pg_log"
    log_sources = []
    if log_dir.is_dir():
        log_sources.extend(sorted(log_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True))
    log_sources.append(pgdata / "pg.log")
    logfiles = [f for f in log_sources if f.is_file()]
    if not logfiles:
        return
    logfile = logfiles[0]
    try:
        lines = logfile.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return
    fatal = [l for l in lines if "FATAL" in l or "ERROR" in l]
    if fatal:
        print(f"           --- Last errors from {logfile.name} ---")
        for l in fatal[-3:]:
            print(f"           {l}")
    last5 = lines[-5:] if len(lines) > 5 else lines
    if last5 and not any("FATAL" in l for l in last5):
        print(f"           --- Last lines from {logfile.name} ---")
        for l in last5:
            print(f"           {l}")

# -- PID Tracking ---------------------------------------------------------------

def _read_pids():
    if PID_FILE.exists():
        try:
            return json.loads(PID_FILE.read_text())
        except (json.JSONDecodeError, KeyError):
            pass
    return {}

def _write_pids(pids):
    PID_FILE.write_text(json.dumps(pids, indent=2))

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

# -- Status ---------------------------------------------------------------------

def _status():
    pids = _read_pids()
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
    return api_alive, vite_alive, pids

def _status_line(name, port, alive):
    dot = _c(C.GRN, ">>") if alive else _c(C.RED, "..")
    lbl = _c(C.GRN, "RUNNING") if alive else _c(C.RED, "STOPPED")
    pid_info = ""
    if alive:
        pids = _read_pids()
        pid = pids.get("vite" if name == "Frontend" else "api")
        if pid:
            pid_info = _c(C.GRY, f"  (PID {pid})")
    return f"  {dot}  {_c(C.B + C.WHT, name):<12}  {_c(C.GRY, f'port {port}'):<10}  {lbl}{pid_info}"

# -- Actions --------------------------------------------------------------------

def _start():
    # Clean up old PID files
    for f in [PID_FILE, ROOT / "data" / "api_bg.pid"]:
        if f.exists():
            try:
                f.unlink()
            except OSError:
                pass

    api_alive, vite_alive, _ = _status()

    if api_alive and vite_alive:
        print(f"  [!] {_c(C.YLW, 'Already running.')}  Use Stop first to restart.")
        return

    # -- PostgreSQL ensure (start if needed, create DB) -------------------------
    print(f"  [~] Checking PostgreSQL...")
    pg_ok = _pg_ensure()
    if pg_ok:
        print(f"       [+] PostgreSQL is ready")
    else:
        print(f"       [..] PostgreSQL not available — API will use file-based data")

    log_handle = None

    # -- Launch API (background) ------------------------------------------------
    if not api_alive:
        print(f"  [~] Starting API server (background)...")
        _kill_port(API_PORT)
        log_file = ROOT / "data" / "api_bg.log"
        log_file.write_text("")  # truncate for fresh start
        log_handle = open(log_file, "a", encoding="utf-8")
        subprocess_env = {**os.environ, "AQC_PASSWORD": os.environ.get("AQC_PASSWORD", "1234")}
        subprocess.Popen(
            [sys.executable, str(ROOT / "data" / "main.py"), "--bg-api"],
            cwd=ROOT, stdout=log_handle, stderr=subprocess.STDOUT,
            env=subprocess_env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

    # -- Launch Frontend (static server, no file watcher) -----------------------
    if not vite_alive:
        print(f"  [~] Starting Frontend...")
        _kill_port(VITE_PORT)
        cmd = ["node", "serve-dist.js"]
        subprocess.Popen(
            cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

    # -- Wait for both ports ----------------------------------------------------
    api_pid = None
    vite_pid = None

    if not api_alive:
        print(f"  [~] Waiting for API server...")
        api_pid = _wait_for_port(API_PORT, timeout=45, label="API")
    else:
        api_pid = _find_pid_by_port(API_PORT)

    if not vite_alive:
        print(f"  [~] Waiting for Frontend...")
        vite_pid = _wait_for_port(VITE_PORT, timeout=30, label="Frontend")
    else:
        vite_pid = _find_pid_by_port(VITE_PORT)

    if log_handle:
        log_handle.close()

    print()

    # -- Report Results ---------------------------------------------------------
    if api_pid:
        print(f"       [+] API server ready on {_c(C.B + C.CYN, f'http://localhost:{API_PORT}')}")
    else:
        print(f"       [!!] API server failed to start")
        bg_log = ROOT / "data" / "api_bg.log"
        if bg_log.exists():
            lines = bg_log.read_text().splitlines()
            fatal = [l for l in lines if any(kw in l.lower() for kw in ("error", "traceback", "fatal"))]
            if fatal:
                print(f"           {_c(C.RED, fatal[-1])}")
        print(f"      Check data/api_bg.log for details.")

    if vite_pid:
        print(f"       [+] Frontend ready on  {_c(C.B + C.CYN, f'http://localhost:{VITE_PORT}')}")
    else:
        print(f"       [!!] Frontend failed to start")

    _write_pids({"api": api_pid, "vite": vite_pid})

    if api_pid and vite_pid:
        print()
        print(f"  [+] {_c(C.B + C.GRN, 'All services started successfully!')}")
    else:
        print()
        print(f"  [!] {_c(C.B + C.YLW, 'Startup partially failed or timed out.')}")

def _stop():
    api_alive, vite_alive, pids = _status()

    # Kill Frontend by PID
    if vite_alive and pids.get("vite"):
        print(f"  [+] Stopping Frontend... {_c(C.GRY, f'(PID {pids["vite"]})')}")
        _kill_pid(pids["vite"])

    # Kill API by PID
    if api_alive and pids.get("api"):
        print(f"  [+] Stopping API server... {_c(C.GRY, f'(PID {pids["api"]})')}")
        _kill_pid(pids["api"])

    # Also kill by api_bg.pid (the background process may have a different PID)
    bg_pid_file = ROOT / "data" / "api_bg.pid"
    if bg_pid_file.exists():
        try:
            bg_pid = int(bg_pid_file.read_text().strip())
            _kill_pid(bg_pid)
            bg_pid_file.unlink(missing_ok=True)
        except (ValueError, OSError):
            pass

    # Kill any remaining processes on ports
    _kill_port(API_PORT)
    _kill_port(VITE_PORT)

    # Stop PostgreSQL cleanly (prevents crash-recovery loops on next start)
    _pg_stop()

    # Clean up PID file
    if PID_FILE.exists():
        PID_FILE.unlink()

    if not api_alive and not vite_alive:
        print(f"  [--] No services were running")
    else:
        print(f"  [+] {_c(C.B + C.GRN, 'All services stopped')}")

# -- Header ---------------------------------------------------------------------

def _header():
    L = C.GRY
    print()
    print(f"  {L}+====================================================================+{C.R}")
    print(f"  {L}|{C.R}  {_c(C.B + C.BLU, 'BDR DASHBOARD')}                         {_c(C.B + C.CYN, 'LAUNCHER')}        {_c(C.GRY, 'v1.2')}  {L}|{C.R}")
    print(f"  {L}|{C.R}  {_c(C.D, 'Start / Stop the full stack - API + Frontend')}               {L}|{C.R}")
    print(f"  {L}+====================================================================+{C.R}")
    print()

def _footer():
    print()
    print(f"  {_c(C.GRY, 'Press Enter to return to menu...')}")
    try:
        input()
    except EOFError:
        pass

# -- Menu -----------------------------------------------------------------------

def _draw_menu():
    _clear()
    _header()

    api_alive, vite_alive, _ = _status()

    print(f"  {_c(C.B + C.WHT, 'SERVICE STATUS')}")
    print(f"  {_c(C.GRY, '----------------------------------------------------------------')}")
    print(_status_line("API", API_PORT, api_alive))
    print(_status_line("Frontend", VITE_PORT, vite_alive))
    print(f"  {_c(C.GRY, '----------------------------------------------------------------')}")
    print()

    if api_alive and vite_alive:
        print(f"  >> {_c(C.B + C.GRN, 'Everything is RUNNING')}")
        print(f"      {_c(C.GRY, 'Dashboard:')}  {_c(C.CYN, f'http://localhost:{VITE_PORT}')}")
        print()
    elif not api_alive and not vite_alive:
        print(f"  .. {_c(C.B + C.RED, 'All services STOPPED')}")
        print()
    else:
        print(f"  [~] {_c(C.B + C.YLW, 'Partially running')}")
        print()

    print(f"  {_c(C.B + C.WHT, 'ACTIONS')}")
    print(f"  {_c(C.GRY, '----------------------------------------------------------------')}")
    print(f"    {_c(C.B + C.CYN, '1')}   {_c(C.WHT, 'Start All')}     {_c(C.D + C.GRY, 'Launch API (bg) + Frontend')}")
    print(f"    {_c(C.B + C.CYN, '2')}   {_c(C.WHT, 'Stop All')}      {_c(C.D + C.GRY, 'Shutdown everything')}")
    print(f"    {_c(C.B + C.CYN, '0')}   {_c(C.WHT, 'Exit')}         {_c(C.D + C.GRY, 'Close this window')}")
    print(f"  {_c(C.GRY, '----------------------------------------------------------------')}")
    print()

# -- Main Loop ------------------------------------------------------------------

def main():
    _clear()
    try:
        while True:
            _draw_menu()
            try:
                choice = input(f"  {_c(C.B + C.CYN, 'Choose')} {_c(C.GRY, '[0-2]')} {_c(C.CYN, '>')}  ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            print()

            try:
                if choice == "1":
                    _start()
                elif choice == "2":
                    _stop()
                elif choice == "0":
                    _pg_stop()
                    print(f"  [+] Goodbye.\n")
                    break
                else:
                    print(f"  [!!] Invalid option")
            except Exception as e:
                print(f"  [!!] Error: {e}")
                import traceback
                traceback.print_exc()
            _footer()
    except KeyboardInterrupt:
        print()
        print(f"  [+] Goodbye.\n")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
