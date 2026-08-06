import csv
import concurrent.futures
import ctypes
import getpass
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import traceback
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import paramiko

_PARENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PARENT))
import postgres_db

VERSION = "2.0.0"
REMOTE_FILE = "~/auto-dfu-tool/assembly_test_app/bdr_session.json"
REMOTE_FILE_RINGS = "~/auto-dfu-tool/assembly_test_app/rings_config.json"
REMOTE_FILE_LOGS_DIR = "~/auto-dfu-tool/ring-manager-data/logs"
REMOTE_WORKDIR = "~/auto-dfu-tool"
REMOTE_COMMAND = (
    "cd ~/auto-dfu-tool && "
    ". .venv/bin/activate && "
    "python3 -m assembly_test_app.bdr_report"
)

AUTH_PASSWORD = os.environ.get("AQC_PASSWORD", "1234")
_env_file = _PARENT / ".env"
if _env_file.exists():
    with open(_env_file, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line.startswith("AQC_PASSWORD="):
                _val = _line.split("=", 1)[1].strip().strip("\"'")
                if _val:
                    AUTH_PASSWORD = _val

AUTO_DOWNLOAD_INTERVAL_SECONDS = 30
AUTO_LOG_COLLECT_INTERVAL_SECONDS = 1800
LOG_FILES_TO_COLLECT = ["app.log", "app.log1"]
ARCHIVE_INTERVAL = 30          # 30 seconds between BDR snapshots
_last_archive_time = 0.0        # last archive timestamp (module-level tracker)
_archive_migrated = False       # one-time flag: old flat date folders → machine/date layout
CONFIG_FILE = _PARENT / "machines.json"
DEFAULT_DESTINATION = r"C:\Users\meshe\Music\BDR DASHBOARD\AQC 47"

DEFAULT_MACHINES = [
    {"name": "aqc-47", "user": "aqc-47", "ip": "172.16.18.71"},
    {"name": "aqc-37", "user": "aqc-37", "ip": "172.16.18.74"},
    {"name": "aqc-46", "user": "aqc-46", "ip": "172.16.18.75"},
    {"name": "aqc-45", "user": "aqc-45", "ip": "172.16.18.72"},
    {"name": "aqc-34", "user": "aqc-34", "ip": "172.16.18.80"},
    {"name": "aqc-48", "user": "aqc-48", "ip": "172.16.18.77"},
]

_APP_DIR = Path(__file__).resolve().parent
BG_PID_DIR = _APP_DIR

BG_DOWNLOAD_PID = BG_PID_DIR / "download_bg.pid"
BG_DOWNLOAD_LOG = BG_PID_DIR / "download_bg.log"

BG_IMPORT_PID = BG_PID_DIR / "import_bg.pid"
BG_IMPORT_LOG = BG_PID_DIR / "import_bg.log"

BG_BOTH_PID = BG_PID_DIR / "both_bg.pid"
BG_BOTH_LOG = BG_PID_DIR / "both_bg.log"

BG_API_PID = BG_PID_DIR / "api_bg.pid"
BG_API_LOG = BG_PID_DIR / "api_bg.log"

BG_LOG_PID = BG_PID_DIR / "logs_bg.pid"
BG_LOG_LOG = BG_PID_DIR / "logs_bg.log"

UPDATER_PID_FILES = (BG_DOWNLOAD_PID, BG_BOTH_PID, BG_API_PID)


def bg_log(log_file, message):
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")


def is_pid_running(pid_file):
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        if os.name == "nt":
            handle = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, pid)
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (ValueError, OSError, ProcessLookupError):
        pid_file.unlink(missing_ok=True)
        return False


def start_background(pid_file, log_file, flag_name):
    if is_pid_running(pid_file):
        return False, "Background process is already running."
    if pid_file in UPDATER_PID_FILES:
        running = other_updater_running(pid_file)
        if running:
            return False, f"Another updater is already running ({running}). Stop it before starting this one."
    pythonw = Path(sys.executable).parent / "pythonw.exe"
    if not pythonw.exists():
        pythonw = sys.executable
    proc = subprocess.Popen(
        [str(pythonw), str(Path(__file__).resolve()), flag_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    pid_file.write_text(str(proc.pid))
    bg_log(log_file, f"Background process started (PID {proc.pid})")
    return True, f"Background process started (PID {proc.pid}). Close this window - it keeps running."


def stop_background(pid_file, log_file):
    if not pid_file.exists():
        return False, "No background process found."
    try:
        pid = int(pid_file.read_text().strip())
        if os.name == "nt":
            ctypes.windll.kernel32.TerminateProcess(
                ctypes.windll.kernel32.OpenProcess(0x0001 | 0x0400, False, pid), 0
            )
        else:
            os.kill(pid, signal.SIGTERM)
        pid_file.unlink(missing_ok=True)
        bg_log(log_file, f"Background process stopped (PID {pid})")
        return True, f"Background process stopped (PID {pid})."
    except Exception as exc:
        pid_file.unlink(missing_ok=True)
        return False, f"Error stopping: {exc}"


def other_updater_running(current_pid_file):
    for pid_file in UPDATER_PID_FILES:
        if pid_file != current_pid_file and is_pid_running(pid_file):
            return pid_file.stem.replace("_bg", "")
    return None





# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

class UI:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    BLUE = "\033[38;5;33m"
    CYAN = "\033[38;5;44m"
    GREEN = "\033[38;5;35m"
    RED = "\033[38;5;160m"
    YELLOW = "\033[38;5;214m"
    WHITE = "\033[38;5;255m"
    GRAY = "\033[38;5;240m"
    MAGENTA = "\033[38;5;200m"
    ORANGE = "\033[38;5;208m"


def enable_ansi():
    if os.name != "nt":
        return
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)
    mode = ctypes.c_ulong()
    if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    kernel32.SetConsoleOutputCP(65001)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def color(text, code):
    return f"{code}{text}{UI.RESET}"


def rule(width=70, style=UI.GRAY):
    return color("-" * width, style)


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def pause():
    input(color("\n  Press Enter to continue...", UI.DIM))


def prompt(label):
    return input(color(label, UI.BOLD + UI.CYAN)).strip()


def print_status(message, status="info"):
    styles = {
        "ok": (UI.GREEN, "OK"),
        "fail": (UI.RED, "FAIL"),
        "warn": (UI.YELLOW, "WARN"),
        "info": (UI.CYAN, "INFO"),
        "step": (UI.MAGENTA, "STEP"),
    }
    style, label = styles[status]
    print(f"  [{color(label, style + UI.BOLD)}]  {message}")


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def config_path():
    return CONFIG_FILE


def load_config():
    path = config_path()
    if not path.exists():
        config = {"destination": DEFAULT_DESTINATION, "machines": DEFAULT_MACHINES}
        save_config(config)
        return config
    with path.open("r", encoding="utf-8") as f:
        config = json.load(f)
    config.setdefault("destination", DEFAULT_DESTINATION)
    config.setdefault("destination_bdr", config["destination"])
    config.setdefault("destination_rings", config["destination"])
    config.setdefault("machines", [])
    return config


def save_config(config):
    with config_path().open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def parse_machine(value):
    value = value.strip()
    match = re.fullmatch(r"([^@\s]+)@([0-9A-Za-z.\-]+)", value)
    if not match:
        raise ValueError("Use this format: aqc-48@172.16.18.77")
    user, ip = match.groups()
    return {"name": user, "user": user, "ip": ip}


def parse_machine_entries(value):
    entries = re.split(r"[\n,;]+", value)
    machines = []
    errors = []
    for line_number, entry in enumerate(entries, start=1):
        entry = entry.strip()
        if not entry:
            continue
        try:
            machines.append(parse_machine(entry))
        except ValueError as exc:
            errors.append(f"Entry {line_number} ({entry}): {exc}")
    if errors:
        raise ValueError("\n".join(errors))
    if not machines:
        raise ValueError("Enter at least one machine.")
    return machines


def safe_filename_part(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._") or "machine"


def remote_path_for_sftp(client, remote_file):
    if not remote_file.startswith("~/"):
        return remote_file
    stdin, stdout, stderr = client.exec_command('printf %s "$HOME"')
    home = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if not home:
        raise RuntimeError(err or "Could not detect remote home directory")
    return f"{home}/{remote_file[2:]}"


# ---------------------------------------------------------------------------
# Download / SFTP
# ---------------------------------------------------------------------------

def run_with_timeout(func, timeout, *args, **kwargs):
    """Run a function with a timeout, raises TimeoutError if it exceeds."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            # Try to cancel the future (best effort)
            future.cancel()
            raise TimeoutError(f"Operation timed out after {timeout}s")

def _categorize_error(exc, remote_path, ip):
    msg = str(exc).lower() if str(exc) else type(exc).__name__.lower()
    if "no such file" in msg or "not found" in msg:
        return "not_found", f"Remote file not found: {remote_path}"
    if "permission denied" in msg:
        return "auth", f"Authentication failed: {exc}"
    if "timeout" in msg or "timed out" in msg:
        return "connect", f"Connection timed out to {ip}: {exc}"
    if "connection refused" in msg or "connection reset" in msg or "connection aborted" in msg:
        return "connect", f"Connection refused by {ip}: {exc}"
    if "authentication failed" in msg or "auth" in msg:
        return "auth", f"Authentication failed for {ip}: {exc}"
    if "name or service not known" in msg or "unreachable" in msg or "host is down" in msg:
        return "connect", f"Host unreachable: {ip}: {exc}"
    return "other", f"{type(exc).__name__}: {exc}"


def _download_one_attempt(machine, password, destination, remote_file):
    """Single attempt to download from one machine. Returns (name, ok, message, label)."""
    name = machine["name"]
    user = machine["user"]
    ip = machine["ip"]
    output_name = f"{safe_filename_part(name)}.json"
    output_path = Path(destination) / output_name
    tmp_path = output_path.with_suffix(f".tmp.{uuid.uuid4().hex[:8]}")
    remote_file_label = "rings" if remote_file == REMOTE_FILE_RINGS else "bdr"
    remote_path = remote_file

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=ip,
            username=user,
            password=password,
            timeout=5,
            banner_timeout=5,
            auth_timeout=5,
            look_for_keys=False,
            allow_agent=False,
        )
        remote_path = remote_path_for_sftp(client, remote_file)
        with client.open_sftp() as sftp:
            sftp.timeout = 5
            try:
                sftp.stat(remote_path)
            except Exception as e:
                cat, detail = _categorize_error(e, remote_path, ip)
                if cat == "not_found" and remote_file_label == "rings":
                    try:
                        dir_list = sftp.listdir(str(Path(remote_path).parent))
                        detail += f" | available files: {', '.join(dir_list[:10])}"
                    except Exception:
                        pass
                return name, False, detail, remote_file_label
            sftp.get(remote_path, str(tmp_path))
        if tmp_path.exists():
            os.replace(str(tmp_path), str(output_path))
        return name, True, str(output_path), remote_file_label
    except Exception as exc:
        cat, detail = _categorize_error(exc, remote_path, ip)
        return name, False, detail, remote_file_label
    finally:
        client.close()
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def download_one(machine, password, destination, remote_file=REMOTE_FILE):
    """Download from one machine with a strict per-machine timeout of 20s."""
    try:
        return run_with_timeout(
            _download_one_attempt, timeout=20,
            machine=machine, password=password,
            destination=destination, remote_file=remote_file,
        )
    except TimeoutError:
        name = machine["name"]
        label = "rings" if remote_file == REMOTE_FILE_RINGS else "bdr"
        return name, False, f"Timeout (20s) for {name}", label


# ---------------------------------------------------------------------------
# Display helpers for the downloader screens
# ---------------------------------------------------------------------------

def header_downloader(config, remote_file=REMOTE_FILE, title="BDR DASHBOARD DOWNLOADER", subtitle="Fast JSON collection from configured AQC machines"):
    clear_screen()
    w = 66
    print()
    print(color("  ." + "-" * w + ".", UI.BLUE))
    for line in [title, subtitle]:
        print(color("  |", UI.BLUE) + color(f" {line}".ljust(w + 1), UI.BOLD + UI.WHITE) + color("|", UI.BLUE))
    print(color("  '" + "-" * w + "'", UI.BLUE))
    print()
    print(f"    {color('Destination', UI.BOLD)}  {config['destination']}")
    print(f"    {color('Remote file', UI.BOLD)}  {remote_file}")
    print(f"    {color('Auto interval', UI.BOLD)}  every 30 sec")
    print()


def list_machines(config):
    print(color("Machines", UI.BOLD + UI.WHITE))
    print(rule())
    if not config["machines"]:
        print_status("No machines configured.", "warn")
        return
    print(f"{color('#', UI.DIM):>3}  {color('Machine', UI.BOLD):<16} {color('User', UI.BOLD):<16} {color('IP Address', UI.BOLD):<18}")
    print(rule())
    for index, machine in enumerate(config["machines"], start=1):
        print(f"{index:>3}  {machine['name']:<16} {machine['user']:<16} {machine['ip']:<18}")


def add_machine(config):
    print()
    value = prompt("Enter machine as user@ip, example aqc-48@172.16.18.77: ")
    machine = parse_machine(value)
    for existing in config["machines"]:
        if existing["name"].lower() == machine["name"].lower():
            existing.update(machine)
            save_config(config)
            print_status(f"Updated {machine['name']}.", "ok")
            return
    config["machines"].append(machine)
    save_config(config)
    print_status(f"Added {machine['name']}.", "ok")


def add_multiple_machines(config):
    print()
    print(color("Enter machines as user@ip.", UI.BOLD + UI.WHITE))
    print(color("Use commas, semicolons, or one machine per line. Submit a blank line to finish.", UI.DIM))
    print(color("Example: aqc-48@172.16.18.77, aqc-49@172.16.18.78", UI.DIM))
    print()
    lines = []
    while True:
        value = prompt("> ")
        if not value:
            break
        lines.append(value)
    machines = parse_machine_entries("\n".join(lines))
    by_name = {machine["name"].lower(): index for index, machine in enumerate(config["machines"])}
    added = 0
    updated = 0
    for machine in machines:
        key = machine["name"].lower()
        if key in by_name:
            config["machines"][by_name[key]].update(machine)
            updated += 1
        else:
            by_name[key] = len(config["machines"])
            config["machines"].append(machine)
            added += 1
    save_config(config)
    print_status(f"Added {added} and updated {updated} machines.", "ok")


def remove_machine(config):
    list_machines(config)
    if not config["machines"]:
        return
    value = prompt("\nEnter number to remove: ")
    if not value.isdigit():
        print_status("Invalid number.", "fail")
        return
    index = int(value)
    if index < 1 or index > len(config["machines"]):
        print_status("Invalid number.", "fail")
        return
    removed = config["machines"].pop(index - 1)
    save_config(config)
    print_status(f"Removed {removed['name']}.", "ok")


def change_destination(config):
    print(f"\nCurrent destination: {color(config['destination'], UI.WHITE)}")
    value = prompt("Enter new destination folder: ").strip('"')
    if not value:
        return
    Path(value).mkdir(parents=True, exist_ok=True)
    config["destination"] = value
    save_config(config)
    print_status("Destination updated.", "ok")


def generate_serial_csv(destination):
    csv_dir = Path(destination)
    json_files = sorted(csv_dir.glob("*.json"))
    if not json_files:
        print_status("No JSON files found in destination.", "warn")
        return None
    rows = []
    for json_path in json_files:
        machine_name = json_path.stem
        try:
            with json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            print_status(f"Skipping {json_path.name}: {exc}", "warn")
            continue
        if not isinstance(data, dict):
            print_status(f"Skipping {json_path.name}: unexpected JSON type ({type(data).__name__})", "warn")
            continue
        slots = data.get("slots", {})
        for slot_key, slot_data in slots.items():
            if not isinstance(slot_data, dict):
                continue
            serial = slot_data.get("serial_number")
            if serial:
                rows.append({"Machine Name": machine_name, "Slot Number": slot_key, "Serial Number": serial})
    if not rows:
        print_status("No serial numbers found in any JSON files.", "warn")
        return None
    csv_path = csv_dir / "all_serial_numbers.csv"
    tmp_path = csv_dir / ".all_serial_numbers.csv.tmp"
    try:
        with tmp_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Machine Name", "Slot Number", "Serial Number"])
            writer.writeheader()
            writer.writerows(rows)
        os.replace(str(tmp_path), str(csv_path))
    except Exception as e:
        print_status(f"Error writing CSV: {e}", "fail")
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        return None
    return csv_path


# ---------------------------------------------------------------------------
# Download / Import core logic
# ---------------------------------------------------------------------------

def download_all(config, password=AUTH_PASSWORD, show_password_prompt=False, remote_file=REMOTE_FILE, destination=None):
    machines = config["machines"]
    destination = destination or config["destination"]
    if not machines:
        print_status("No machines configured.", "warn")
        return False
    subdir = "rings" if remote_file == REMOTE_FILE_RINGS else "bdr"
    dest_path = Path(destination) / subdir
    dest_path.mkdir(parents=True, exist_ok=True)

    # Clean any orphaned .tmp.* files from previous failed downloads
    for tmp in dest_path.glob("*.tmp.*"):
        try:
            tmp.unlink()
        except OSError:
            pass

    print(color("Download Summary", UI.BOLD + UI.WHITE))
    print(rule())
    print(f'{color("Destination", UI.BOLD)}  {dest_path}')
    print(f'{color("Remote file", UI.BOLD)}  {remote_file}')
    print(f'{color("Machines", UI.BOLD)}     {len(machines)} configured')
    print(rule())
    print()
    if show_password_prompt:
        password = getpass.getpass(color("Enter common password: ", UI.BOLD + UI.CYAN))
    if not password:
        print_status("Password is required.", "fail")
        return False
    print()
    print_status("Downloading in parallel (max 25s per machine)...", "info")
    ok_count = 0
    fail_count = 0
    fail_names = []
    workers = min(16, len(machines))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(download_one, machine, password, str(dest_path), remote_file) for machine in machines]
        done, not_done = concurrent.futures.wait(futures, timeout=45)
        for future in not_done:
            future.cancel()
        for completed, future in enumerate(done, start=1):
            try:
                name, ok, message, _ = future.result()
                prefix = f"{completed}/{len(machines)}"
                if ok:
                    ok_count += 1
                    print_status(f"{prefix}  {name:<10} saved", "ok")
                else:
                    fail_count += 1
                    fail_names.append(name)
                    print_status(f"{prefix}  {name:<10} {message[:200]}", "fail")
            except Exception as exc:
                fail_count += 1
                print_status(f"{completed}/{len(machines)}  machine failed: {exc}", "fail")
        fail_count += len(not_done)
    print()
    print(rule())
    if fail_count:
        print_status(f"Finished with {ok_count} successful and {fail_count} failed downloads.", "warn")
        print(color(f"  Failed machines: {', '.join(fail_names)}", UI.DIM))
    else:
        print_status(f"Finished successfully. {ok_count} files downloaded.", "ok")

    # -- Clean stale data for failed machines (e.g. machine was reset) ----------
    if fail_names:
        print_status("Removing stale data for failed machines...", "info")
        for name in fail_names:
            json_path = dest_path / f"{safe_filename_part(name)}.json"
            if json_path.exists():
                try:
                    json_path.unlink()
                except OSError:
                    pass
            if remote_file == REMOTE_FILE_RINGS:
                postgres_db._delete_rings_machine(name)
            else:
                postgres_db._delete_bdr_machine(name)
        print()

    if ok_count:
        print()
        print_status("Generating CSV with all serial numbers...", "info")
        csv_path = generate_serial_csv(str(dest_path))
        if csv_path:
            print_status(f"Saved serial numbers CSV: {csv_path}", "ok")
    # -- Archive BDR snapshot (rate-limited to once per 10 min) ------------
    if remote_file == REMOTE_FILE:
        archive_bdr_snapshot(dest_path)

    return fail_count == 0


def _migrate_flat_archive(archive_root):
    """One-time migration: move files from old flat YYYY-MM-DD/ folders into
    the correct machine/YYYY-MM-DD/ layout.

    Old format:  archive/2026-06-25/00-00-36_aqc-06.json
    New format:  archive/aqc-06/2026-06-25/00-00-36.json
    """
    global _archive_migrated
    if _archive_migrated or not archive_root.is_dir():
        return
    date_pat = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    migrated = 0
    for entry in sorted(archive_root.iterdir()):
        if not entry.is_dir() or not date_pat.match(entry.name):
            continue
        date_str = entry.name
        for old_file in sorted(entry.iterdir()):
            if not old_file.is_file() or old_file.suffix != ".json":
                continue
            # old filename: HH-MM-SS_machine-name.json
            parts = old_file.stem.split("_", 1)
            if len(parts) != 2:
                continue
            time_str, machine_name = parts
            target_dir = archive_root / machine_name / date_str
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / f"{time_str}.json"
            shutil.move(str(old_file), str(target_file))
            migrated += 1
        # Remove the now-empty flat date folder
        try:
            entry.rmdir()
        except OSError:
            pass
    if migrated:
        print(f"       [+] Migrated {migrated} archived files to machine/date layout")
    _archive_migrated = True


def archive_bdr_snapshot(dest_path):
    """Copy current BDR JSON files to DESTINATION/archive/<machine>/YYYY-MM-DD/HH-MM-SS.json.

    Rate-limited to once per ARCHIVE_INTERVAL seconds so it's safe to call
    from any download entry point (manual, auto, background loop).
    """
    global _last_archive_time
    now = time.time()
    if now - _last_archive_time < ARCHIVE_INTERVAL:
        return
    _last_archive_time = now

    archive_root = dest_path.parent / "archive"
    _migrate_flat_archive(archive_root)

    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H-%M-%S")

    count = 0
    copied_files = []
    for json_path in sorted(dest_path.glob("*.json")):
        machine_name = json_path.stem
        archive_dir = archive_root / machine_name / date_str
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_name = f"{time_str}.json"
        dest_file = archive_dir / archive_name
        shutil.copy2(str(json_path), str(dest_file))
        copied_files.append(str(dest_file))
        count += 1

    if count:
        print(f"       [+] Archived {count} BDR files to {archive_root}")

        # Upsert into ring_status (latest-state table)
        try:
            from ring_status import ingest_file_to_ring_status
            pg_conn = postgres_db.get_connection()
            rs_count = 0
            for fpath in copied_files:
                try:
                    rs_count += ingest_file_to_ring_status(pg_conn, fpath)
                except Exception:
                    pass
            pg_conn.commit()
            pg_conn.close()
            if rs_count:
                print(f"       [+] ring_status: upserted {rs_count} rows")
        except Exception:
            pass

        import urllib.request
        for fpath in copied_files:
            try:
                body = json.dumps({"file_path": fpath}).encode("utf-8")
                req = urllib.request.Request(
                    "http://127.0.0.1:8000/api/old-data/ingest-file",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=5)
            except Exception:
                pass


def download_both(config, password=AUTH_PASSWORD, show_password_prompt=False):
    if show_password_prompt:
        password = getpass.getpass(color("Enter common password: ", UI.BOLD + UI.CYAN))
    if not password:
        print_status("Password is required.", "fail")
        return False
    print()
    print_status("Downloading BDR + Rings in parallel...", "step")
    results = {}
    def _run_bdr():
        try:
            results["bdr"] = download_all(config, password=password, remote_file=REMOTE_FILE, destination=config.get("destination_bdr"))
        except Exception as e:
            print_status(f"BDR download failed: {e}", "fail")
            results["bdr"] = False
    def _run_rings():
        try:
            results["rings"] = download_all(config, password=password, remote_file=REMOTE_FILE_RINGS, destination=config.get("destination_rings"))
        except Exception as e:
            print_status(f"Rings download failed: {e}", "fail")
            results["rings"] = False
    t1 = threading.Thread(target=_run_bdr, daemon=True)
    t2 = threading.Thread(target=_run_rings, daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    ok = results.get("bdr", False) and results.get("rings", False)
    return ok


def wait_for_next_run(seconds):
    next_run = datetime.now() + timedelta(seconds=seconds)
    print()
    print_status(f"Next automatic download starts at {next_run.strftime('%H:%M:%S')}. Press Ctrl+C to stop auto mode.", "info")
    try:
        while seconds > 0:
            minutes, remaining_seconds = divmod(seconds, 60)
            print(color(f"\rWaiting {minutes:02d}:{remaining_seconds:02d} until next run...", UI.DIM), end="", flush=True)
            time.sleep(1)
            seconds -= 1
        print()
        return True
    except KeyboardInterrupt:
        print()
        print_status("Automatic download stopped.", "warn")
        return False


def auto_download(config, remote_file=REMOTE_FILE, tool_title="BDR DASHBOARD DOWNLOADER", tool_subtitle="Fast JSON collection from configured AQC machines"):
    while True:
        header_downloader(config, remote_file, tool_title, tool_subtitle)
        print_status(f"Automatic mode is running with password {AUTH_PASSWORD!r}. Press Ctrl+C to return to the menu.", "info")
        print()
        download_all(config, remote_file=remote_file)
        if not wait_for_next_run(AUTO_DOWNLOAD_INTERVAL_SECONDS):
            return


def bg_download_loop(config, log_file, pid_file, remote_file=REMOTE_FILE, title="Download"):
    pid_file.write_text(str(os.getpid()))
    bg_log(log_file, f"Background {title} loop started")
    last_cycle = time.time()
    while True:
        try:
            run_with_timeout(download_all, timeout=50, config=config, remote_file=remote_file)
            last_cycle = time.time()
            bg_log(log_file, f"Download cycle completed")
        except TimeoutError:
            bg_log(log_file, "Download cycle timed out (50s)")
        except Exception as exc:
            bg_log(log_file, f"Download cycle error: {exc}")
        wait = max(5, AUTO_DOWNLOAD_INTERVAL_SECONDS - int(time.time() - last_cycle))
        bg_log(log_file, f"Waiting {wait}s...")
        for _ in range(wait):
            time.sleep(1)


def bg_import_loop(config, log_file, pid_file):
    pid_file.write_text(str(os.getpid()))
    bg_log(log_file, "Background database import loop started")
    while True:
        try:
            bdr_dest = config.get("destination_bdr", config["destination"])
            rings_dest = config.get("destination_rings", config["destination"])
            import_from_destination(config, bdr_dest, rings_dest)
            bg_log(log_file, f"Import cycle completed, waiting {AUTO_DOWNLOAD_INTERVAL_SECONDS}s...")
            for _ in range(AUTO_DOWNLOAD_INTERVAL_SECONDS):
                time.sleep(1)
        except Exception as exc:
            bg_log(log_file, f"Import cycle error: {exc}")
            time.sleep(AUTO_DOWNLOAD_INTERVAL_SECONDS)


def import_from_destination(config, bdr_dest, rings_dest):
    _ensure_db()
    if not postgres_db.is_available():
        print_status("PostgreSQL not available, skipping import.", "warn")
        return
    bdr_ok = 0
    bdr_removed = 0
    rings_ok = 0
    rings_removed = 0
    print_status("Importing BDR JSON files to PostgreSQL...", "info")
    for machine in config["machines"]:
        name = machine["name"]
        json_path = Path(bdr_dest) / "bdr" / f"{safe_filename_part(name)}.json"
        if json_path.exists() and json_path.stat().st_size > 0:
            data = postgres_db._safe_load_json(json_path)
            if data is not None and postgres_db._has_any_occupied_slots(data):
                postgres_db.import_bdr_json_to_pg(name, json_path)
                bdr_ok += 1
            else:
                postgres_db._delete_bdr_machine(name)
                bdr_removed += 1
        else:
            postgres_db._delete_bdr_machine(name)
            bdr_removed += 1
    print_status("Importing Rings JSON files to PostgreSQL...", "info")
    for machine in config["machines"]:
        name = machine["name"]
        json_path = Path(rings_dest) / "rings" / f"{safe_filename_part(name)}.json"
        if json_path.exists() and json_path.stat().st_size > 0:
            data = postgres_db._safe_load_json(json_path)
            if data is not None and postgres_db._has_any_occupied_slots(data):
                postgres_db.import_rings_json_to_pg(name, json_path)
                rings_ok += 1
            else:
                postgres_db._delete_rings_machine(name)
                rings_removed += 1
        else:
            postgres_db._delete_rings_machine(name)
            rings_removed += 1
    print_status(f"Database import completed. BDR: {bdr_ok} ok, {bdr_removed} removed | Rings: {rings_ok} ok, {rings_removed} removed", "ok")


def run_both_sync(config):
    password = getpass.getpass(color("Enter common password: ", UI.BOLD + UI.CYAN))
    if not password:
        print_status("Password is required.", "fail")
        return False
    ok = True
    print()
    print_status("=== Phase 1: Download BDR + Rings ===", "step")
    if not download_both(config, password=password):
        ok = False
    # download_both calls download_all which already imports to PostgreSQL
    print()
    print_status("Both download and database hosting completed!" if ok else "Completed with some errors.", "ok" if ok else "warn")
    return ok


def bg_both_loop(config, log_file, pid_file):
    pid_file.write_text(str(os.getpid()))
    bg_log(log_file, "Background Both (download + import) loop started")
    last_cycle = time.time()
    while True:
        try:
            run_with_timeout(download_both, timeout=55, config=config)
            last_cycle = time.time()
            bg_log(log_file, "Both cycle completed successfully")
        except TimeoutError:
            bg_log(log_file, "Both cycle timed out (25s)")
        except Exception as exc:
            bg_log(log_file, f"Both cycle error: {exc}")
        wait = max(5, AUTO_DOWNLOAD_INTERVAL_SECONDS - int(time.time() - last_cycle))
        bg_log(log_file, f"Waiting {wait}s...")
        for _ in range(wait):
            time.sleep(1)


# ---------------------------------------------------------------------------
# Log Collection
# ---------------------------------------------------------------------------

def download_machine_log(machine, password, log_file_name, dest_dir):
    """Fetch a single log file from a machine via SFTP."""
    name = machine["name"]
    user = machine["user"]
    ip = machine["ip"]
    output_name = f"{safe_filename_part(name)}_{log_file_name}"
    output_path = Path(dest_dir) / output_name
    tmp_path = output_path.with_suffix(f".tmp.{uuid.uuid4().hex[:8]}")
    remote_path = f"{REMOTE_FILE_LOGS_DIR}/{log_file_name}"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=ip,
            username=user,
            password=password,
            timeout=15,
            banner_timeout=15,
            auth_timeout=15,
            look_for_keys=False,
            allow_agent=False,
        )
        remote_full = remote_path_for_sftp(client, remote_path)
        with client.open_sftp() as sftp:
            sftp.get(remote_full, str(tmp_path))
        if tmp_path.exists():
            os.replace(str(tmp_path), str(output_path))
        file_size = output_path.stat().st_size if output_path.exists() else 0
        return name, True, str(output_path), file_size
    except Exception as exc:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        return name, False, str(exc), 0
    finally:
        client.close()


def collect_all_machine_logs(config, password=AUTH_PASSWORD):
    """Collect app.log and app.log1 from all machines."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M")
    destination = config.get("destination")
    if not destination:
        print_status("No destination configured.", "fail")
        return False
    base_dir = Path(destination) / date_str / time_str
    base_dir.mkdir(parents=True, exist_ok=True)

    machines = config.get("machines", [])
    if not machines:
        print_status("No machines configured.", "warn")
        return False

    print_status(f"Collecting logs from {len(machines)} machines...", "info")
    print(f"    {color('Destination', UI.BOLD)}  {base_dir}")

    ok_count = 0
    fail_count = 0
    workers = min(8, len(machines))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = []
        for machine in machines:
            for log_file in LOG_FILES_TO_COLLECT:
                futures.append(executor.submit(download_machine_log, machine, password, log_file, str(base_dir)))
        for completed, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            name, ok, message, file_size = future.result()
            if ok:
                ok_count += 1
                # Find which machine and log file this was
                machine_entry = None
                log_name = ""
                for m in machines:
                    if m["name"] == name:
                        machine_entry = m
                        break
                if machine_entry:
                    for lf in LOG_FILES_TO_COLLECT:
                        if lf in message:
                            log_name = lf
                            break
                        if f"{safe_filename_part(name)}_{lf}" in message:
                            log_name = lf
                            break
                    if log_name:
                        storage_path = message
                        postgres_db.save_log_metadata(
                            machine_name=name,
                            machine_ip=machine_entry.get("ip", ""),
                            file_name=log_name,
                            file_size=file_size,
                            storage_location=storage_path,
                            collection_status="success"
                        )
                print_status(f"{completed}/{len(futures)}  {name:<10} {log_name} saved", "ok")
            else:
                fail_count += 1
                # Try to find which machine
                machine_entry = None
                log_name = ""
                for m in machines:
                    if m["name"] == name:
                        machine_entry = m
                        break
                if machine_entry:
                    for lf in LOG_FILES_TO_COLLECT:
                        if lf in message:
                            log_name = lf
                            break
                    postgres_db.save_log_metadata(
                        machine_name=name,
                        machine_ip=machine_entry.get("ip", ""),
                        file_name=log_name or "unknown",
                        file_size=0,
                        storage_location="",
                        collection_status="failed",
                        error_message=message
                    )
                print_status(f"{completed}/{len(futures)}  {name:<10} {log_name or ''} {message}", "fail")

    print()
    if fail_count:
        print_status(f"Log collection finished: {ok_count} ok, {fail_count} failed.", "warn")
    else:
        print_status(f"Log collection finished successfully: {ok_count} files.", "ok")
    return fail_count == 0


def bg_log_collect_loop(config, log_file, pid_file):
    """Background loop for log collection every 30 minutes."""
    pid_file.write_text(str(os.getpid()))
    bg_log(log_file, "Background log collection loop started (every 30 min)")
    while True:
        try:
            collect_all_machine_logs(config)
            bg_log(log_file, f"Log collection cycle completed, waiting {AUTO_LOG_COLLECT_INTERVAL_SECONDS}s...")
            for _ in range(AUTO_LOG_COLLECT_INTERVAL_SECONDS):
                time.sleep(1)
        except Exception as exc:
            bg_log(log_file, f"Log collection cycle error: {exc}")
            time.sleep(AUTO_LOG_COLLECT_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# API Server
# ---------------------------------------------------------------------------

def run_api_server():
    sys.path.insert(0, str(_PARENT))
    import uvicorn
    from api import app
    print_status("Starting API server on http://0.0.0.0:8000", "info")

    def run_server():
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print_status("API server started, auto-updating every 10s...", "info")

    try:
        while True:
            config = load_config()
            try:
                download_all(config, remote_file=REMOTE_FILE, destination=config.get("destination_bdr"))
            except Exception as e:
                print_status(f"BDR download error: {e}", "fail")
            try:
                download_all(config, remote_file=REMOTE_FILE_RINGS, destination=config.get("destination_rings"))
            except Exception as e:
                print_status(f"Rings download error: {e}", "fail")

            print_status(f"Auto-update cycle completed, waiting {AUTO_DOWNLOAD_INTERVAL_SECONDS}s...", "info")
            for _ in range(AUTO_DOWNLOAD_INTERVAL_SECONDS):
                time.sleep(1)
    except KeyboardInterrupt:
        print_status("API server stopped.", "warn")


def _kill_port(port):
    """Kill any process listening on the given port."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 5 and f":{port}" in parts[1] and parts[3] == "LISTENING":
                pid = parts[4]
                try:
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, timeout=5)
                except Exception:
                    pass
    except Exception:
        pass


def bg_api_loop(log_file, pid_file):
    last_successful_cycle = time.time()
    try:
        pid_file.unlink(missing_ok=True)
        pid_file.write_text(str(os.getpid()))
        bg_log(log_file, "API server background loop started")
        bg_log(log_file, "Killing any existing process on port 8000...")
        _kill_port(8000)
        sys.path.insert(0, str(_PARENT))
        import uvicorn
        from api import app
        config = load_config()

        def run_server():
            uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        bg_log(log_file, "API server started on http://0.0.0.0:8000, background loop waiting 5s for warmup...")

        time.sleep(5)

        while True:
            if not server_thread.is_alive():
                bg_log(log_file, "API server thread died unexpectedly. Exiting for PM2 restart.")
                break
            try:
                bg_log(log_file, "Starting background data update cycle...")
                try:
                    run_with_timeout(download_both, timeout=55, config=config)
                    last_successful_cycle = time.time()
                    bg_log(log_file, "Auto-update cycle completed successfully")
                except TimeoutError as te:
                    bg_log(log_file, f"Auto-update cycle timed out: {te}")
                wait = max(5, AUTO_DOWNLOAD_INTERVAL_SECONDS - int(time.time() - last_successful_cycle))
                bg_log(log_file, f"Waiting {wait}s...")
                for _ in range(wait):
                    time.sleep(1)
            except Exception as exc:
                tb = traceback.format_exc()
                for tb_line in tb.splitlines():
                    bg_log(log_file, tb_line)
                bg_log(log_file, f"Auto-update cycle error: {exc}")
                time.sleep(AUTO_DOWNLOAD_INTERVAL_SECONDS)
    except Exception as exc:
        bg_log(log_file, f"Fatal startup error: {exc}")
        traceback.print_exc()
        pid_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main_menu():
    enable_ansi()
    while True:
        clear_screen()
        config = load_config()

        dl_bg = is_pid_running(BG_DOWNLOAD_PID)
        both_bg = is_pid_running(BG_BOTH_PID)
        api_bg = is_pid_running(BG_API_PID)
        logs_bg = is_pid_running(BG_LOG_PID)

        dl_indicator = color("*", UI.GREEN) if dl_bg else color("*", UI.RED)
        both_indicator = color("*", UI.GREEN) if both_bg else color("*", UI.RED)
        api_indicator = color("*", UI.GREEN) if api_bg else color("*", UI.RED)
        logs_indicator = color("*", UI.GREEN) if logs_bg else color("*", UI.RED)

        print()
        print(color("  ----- BDR BACKEND v" + VERSION + " -----", UI.BLUE + UI.BOLD))
        print(color("    Download | Database | API Server", UI.CYAN))
        print()
        print(color("  --- DOWNLOAD ------------------------------", UI.MAGENTA))
        print(f"    {color('1.', UI.CYAN)}  Download BDR + Rings (one-shot)")
        print(f"    {color('2.', UI.CYAN)}  Auto-download every 30s    {color('[Ctrl+C to stop]', UI.DIM)}")
        print(f"    {color('Bg:', UI.DIM)} {dl_indicator}  {color('3.', UI.CYAN)} Start bg  {color('4.', UI.CYAN)} Stop bg")
        print()
        print(color("  --- DATABASE ------------------------------", UI.MAGENTA))
        print(f"    {color('5.', UI.CYAN)}  Download both + Import to DB (one-shot)")
        print(f"    {color('Bg:', UI.DIM)} {both_indicator}  {color('6.', UI.CYAN)} Start bg  {color('7.', UI.CYAN)} Stop bg")
        print()
        print(color("  --- API SERVER ----------------------------", UI.MAGENTA))
        print(f"    {color('8.', UI.CYAN)}  Start API server (foreground, port 8000)")
        print(f"    {color('Bg:', UI.DIM)} {api_indicator}  {color('9.', UI.CYAN)} Start bg  {color('10.', UI.CYAN)} Stop bg")
        print()
        print(color("  --- LOG COLLECTION ------------------------", UI.MAGENTA))
        print(f"    {color('11.', UI.CYAN)}  Collect logs (one-shot)")
        print(f"    {color('Bg:', UI.DIM)} {logs_indicator}  {color('12.', UI.CYAN)} Start bg  {color('13.', UI.CYAN)} Stop bg")
        print()
        print(color("  --- MACHINES ------------------------------", UI.MAGENTA))
        print(f"    {color('14.', UI.CYAN)}  Add / update machine(s)")
        print(f"    {color('15.', UI.CYAN)}  Remove machine")
        print(f"    {color('16.', UI.CYAN)}  List all machines")
        print(f"    {color('17.', UI.CYAN)}  Change destination folder")
        print()
        print(color("  --- SYSTEM --------------------------------", UI.MAGENTA))
        print(f"    {color('18.', UI.RED)}  Exit")
        print()

        try:
            choice = prompt("  Select option: ").strip()

            if choice == "1":
                download_both(config)
                pause()
            elif choice == "2":
                while True:
                    clear_screen()
                    header_downloader(config, title="AUTO DOWNLOAD BOTH", subtitle="Downloading BDR + Rings every 30s")
                    print_status("Press Ctrl+C to stop auto mode.", "info")
                    print()
                    download_both(config)
                    if not wait_for_next_run(AUTO_DOWNLOAD_INTERVAL_SECONDS):
                        break
                pause()
            elif choice == "3":
                ok, msg = start_background(BG_DOWNLOAD_PID, BG_DOWNLOAD_LOG, "--bg-download")
                print_status(msg, "ok" if ok else "fail")
                pause()
            elif choice == "4":
                ok, msg = stop_background(BG_DOWNLOAD_PID, BG_DOWNLOAD_LOG)
                print_status(msg, "ok" if ok else "fail")
                pause()
            elif choice == "5":
                run_both_sync(config)
                pause()
            elif choice == "6":
                ok, msg = start_background(BG_BOTH_PID, BG_BOTH_LOG, "--bg-both")
                print_status(msg, "ok" if ok else "fail")
                pause()
            elif choice == "7":
                ok, msg = stop_background(BG_BOTH_PID, BG_BOTH_LOG)
                print_status(msg, "ok" if ok else "fail")
                pause()
            elif choice == "8":
                run_api_server()
                pause()
            elif choice == "9":
                ok, msg = start_background(BG_API_PID, BG_API_LOG, "--bg-api")
                print_status(msg, "ok" if ok else "fail")
                pause()
            elif choice == "10":
                ok, msg = stop_background(BG_API_PID, BG_API_LOG)
                print_status(msg, "ok" if ok else "fail")
                pause()
            elif choice == "11":
                clear_screen()
                print(color("  --- LOG COLLECTION -----------------------", UI.MAGENTA))
                collect_all_machine_logs(config)
                pause()
            elif choice == "12":
                ok, msg = start_background(BG_LOG_PID, BG_LOG_LOG, "--bg-logs")
                print_status(msg, "ok" if ok else "fail")
                pause()
            elif choice == "13":
                ok, msg = stop_background(BG_LOG_PID, BG_LOG_LOG)
                print_status(msg, "ok" if ok else "fail")
                pause()
            elif choice == "14":
                clear_screen()
                list_machines(config)
                print()
                print(color("  --- ADD / UPDATE MACHINE ----------------", UI.MAGENTA))
                print(f"    {color('1.', UI.CYAN)}  Single machine")
                print(f"    {color('2.', UI.CYAN)}  Multiple machines")
                print(f"    {color('0.', UI.CYAN)}  Back")
                print()
                sub = prompt("  Choose: ")
                if sub == "1":
                    add_machine(config)
                elif sub == "2":
                    add_multiple_machines(config)
                pause()
            elif choice == "15":
                clear_screen()
                list_machines(config)
                remove_machine(config)
                pause()
            elif choice == "16":
                clear_screen()
                list_machines(config)
                pause()
            elif choice == "17":
                change_destination(config)
                pause()
            elif choice == "18":
                clear_screen()
                print(color("\n    Thank you for using BDR BACKEND!", UI.BOLD + UI.GREEN))
                print(color("    Goodbye.\n", UI.DIM))
                return 0
            else:
                print_status("Invalid option.", "fail")
                pause()
        except KeyboardInterrupt:
            print()
            print_status("Cancelled.", "warn")
            pause()
        except Exception as exc:
            print_status(f"Error: {exc}", "fail")
            pause()


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

_DB_INITED = False


def _ensure_db():
    global _DB_INITED
    if _DB_INITED:
        return True
    result = [False]

    def _init():
        try:
            postgres_db.init_db()
            result[0] = True
        except Exception:
            pass

    t = threading.Thread(target=_init, daemon=True)
    t.start()
    t.join(timeout=8)
    _DB_INITED = True
    return result[0]


def main():
    if "--bg-download" in sys.argv:
        config = load_config()
        bg_download_loop(config, BG_DOWNLOAD_LOG, BG_DOWNLOAD_PID)
        return 0
    if "--bg-import" in sys.argv:
        config = load_config()
        bg_import_loop(config, BG_IMPORT_LOG, BG_IMPORT_PID)
        return 0
    if "--bg-both" in sys.argv:
        config = load_config()
        bg_both_loop(config, BG_BOTH_LOG, BG_BOTH_PID)
        return 0
    if "--bg-api" in sys.argv:
        if "--start-pg" in sys.argv:
            from bdr import _pg_ensure
            print("[main] Ensuring PostgreSQL is running...")
            if _pg_ensure():
                print("[main] PostgreSQL ready.")
            else:
                print("[main] PostgreSQL failed to start.")
        bg_api_loop(BG_API_LOG, BG_API_PID)
        return 0
    if "--bg-logs" in sys.argv:
        config = load_config()
        bg_log_collect_loop(config, BG_LOG_LOG, BG_LOG_PID)
        return 0
    try:
        return main_menu()
    except KeyboardInterrupt:
        print()
        print(color("\n  Goodbye.", UI.DIM))
        return 1
    except Exception:
        print_status("Unexpected error:", "fail")
        traceback.print_exc()
        input("Press Enter to exit...")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
