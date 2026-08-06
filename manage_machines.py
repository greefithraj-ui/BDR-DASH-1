#!/usr/bin/env python3
"""
Manage machines: add or remove them from the system.
Handles machines.json, data download (BDR + rings + archive), and PostgreSQL sync.

Usage:
    python manage_machines.py add <name> <user> <ip>
    python manage_machines.py add --reload <name> <user> <ip>
    python manage_machines.py remove <name>

Examples:
    python manage_machines.py add aqc-99 aqc-99 172.16.18.99
    python manage_machines.py add --reload aqc-51 aqc-51 172.16.18.127
    python manage_machines.py remove aqc-99
"""

import json
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent


def _install_error_handler():
    """Keep the console window open and show the error on any crash."""
    def _hook(etype, value, tb):
        traceback.print_exception(etype, value, tb)
        if sys.stdin.isatty():
            try:
                input("\nPress Enter to exit...")
            except (EOFError, KeyboardInterrupt):
                pass
    sys.excepthook = _hook


_install_error_handler()


def _find_project_root(start):
    """Walk up from the script until we find the real project root (data/main.py)."""
    current = Path(start).resolve()
    while True:
        if (current / "data" / "main.py").exists():
            return current
        if current.parent == current:
            return None
        current = current.parent
    return None


_ROOT = _find_project_root(_SCRIPT_DIR) or _SCRIPT_DIR
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "data"))

from main import (
    REMOTE_FILE, REMOTE_FILE_RINGS,
    AUTH_PASSWORD, download_one, archive_bdr_snapshot,
    load_config, save_config, safe_filename_part,
)
from data.postgres_db import sync_machines_from_files, _delete_bdr_machine, _delete_rings_machine


def pause():
    if sys.stdin.isatty():
        try:
            input("\nPress Enter to exit...")
        except (EOFError, KeyboardInterrupt):
            pass


def pause_continue():
    if sys.stdin.isatty():
        try:
            input("\n  Press Enter to continue...")
        except (EOFError, KeyboardInterrupt):
            pass


def _password():
    pw = os.environ.get("AQC_PASSWORD", "")
    if not pw:
        _env = _ROOT / ".env"
        if _env.exists():
            for line in _env.read_text().splitlines():
                line = line.strip()
                if line.startswith("AQC_PASSWORD="):
                    pw = line.split("=", 1)[1].strip().strip("\"'")
                    break
    return pw or "1234"


def add_machine(name, user, ip, reload_existing=False):
    password = _password()
    config = load_config()
    machines = config.setdefault("machines", [])

    existing = next((m for m in machines if m["name"] == name), None)
    if existing:
        if reload_existing:
            existing["user"] = user
            existing["ip"] = ip
            save_config(config)
            print(f"[~] Updated existing '{name}' in machines.json")
        else:
            print(f"[!] Machine '{name}' already exists in machines.json")
            print(f"    Use '--reload' to re-download data for an existing machine")
            return False
    else:
        machine = {"name": name, "user": user, "ip": ip}
        machines.append(machine)
        save_config(config)
        print(f"[+] Added '{name}' to machines.json")

    dest_base = Path(config.get("destination_bdr") or config["destination"])
    bdr_dir = dest_base / "bdr"
    rings_dir = dest_base / "rings"
    bdr_dir.mkdir(parents=True, exist_ok=True)
    rings_dir.mkdir(parents=True, exist_ok=True)

    machine_entry = existing or machine

    bdr_ok = False
    rings_ok = False
    bdr_path = bdr_dir / (safe_filename_part(name) + ".json")
    rings_path = rings_dir / (safe_filename_part(name) + ".json")

    print(f"[*] Downloading BDR data for '{name}'...")
    _name, ok, msg, label = download_one(machine_entry, password, bdr_dir, REMOTE_FILE)
    bdr_ok = ok and bdr_path.exists()
    if bdr_ok:
        file_size = bdr_path.stat().st_size
        print(f"    [+] BDR: OK ({file_size} bytes) -> {bdr_path.name}")
    else:
        print(f"    [-] BDR: {msg}")

    print(f"[*] Downloading rings data for '{name}'...")
    _name, ok, msg, label = download_one(machine_entry, password, rings_dir, REMOTE_FILE_RINGS)
    rings_ok = ok and rings_path.exists()
    if rings_ok:
        file_size = rings_path.stat().st_size
        print(f"    [+] Rings: OK ({file_size} bytes) -> {rings_path.name}")
    else:
        print(f"    [-] Rings: {msg}")

    if bdr_ok:
        print(f"[*] Archiving BDR snapshot...")
        archive_bdr_snapshot(bdr_dir)

    print(f"[*] Syncing to PostgreSQL...")
    try:
        sync_machines_from_files()
        print(f"    [+] PostgreSQL sync complete")
    except Exception as e:
        print(f"    [-] PostgreSQL sync error: {e}")

    if bdr_ok or rings_ok:
        print(f"\n[+] Machine '{name}' ({user}@{ip}) added successfully.")
        if bdr_ok:
            print(f"    BDR:  {bdr_path}")
        if rings_ok:
            print(f"    Rings: {rings_path}")
        return True
    else:
        print(f"\n[-] Machine '{name}' was added to config but data download failed.")
        print(f"    Check connectivity and password, then run with --reload")
        return False


def remove_machine(name):
    config = load_config()
    machines = config.setdefault("machines", [])
    before = len(machines)
    config["machines"] = [m for m in machines if m["name"] != name]

    if len(config["machines"]) == before:
        print(f"[!] Machine '{name}' not found in machines.json")
        return False

    save_config(config)
    print(f"[-] Removed '{name}' from machines.json")

    dest_base = Path(config.get("destination_bdr") or config["destination"])
    safe_name = safe_filename_part(name)

    for subdir, label in [("bdr", "BDR"), ("rings", "Rings")]:
        fp = dest_base / subdir / f"{safe_name}.json"
        if fp.exists():
            fp.unlink()
            print(f"    [-] Deleted {label}: {fp}")

    csv_path = dest_base / "bdr" / "all_serial_numbers.csv"
    if csv_path.exists():
        try:
            lines = csv_path.read_text().splitlines()
            kept = [l for l in lines if not l.split(",")[0].strip().strip('"') == name]
            if len(kept) != len(lines):
                csv_path.write_text("\n".join(kept))
                print(f"    [-] Removed '{name}' from {csv_path.name}")
        except Exception:
            pass

    archive_dir = dest_base / "archive" / name
    if archive_dir.exists():
        shutil.rmtree(archive_dir)
        print(f"    [-] Deleted archive: {archive_dir}")

    print(f"[*] Removing from PostgreSQL...")
    try:
        _delete_bdr_machine(name)
        _delete_rings_machine(name)
        print(f"    [+] PostgreSQL rows deleted")
    except Exception as e:
        print(f"    [-] PostgreSQL error: {e}")

    print(f"\n[-] Machine '{name}' fully removed.")
    return True


def main():
    if len(sys.argv) >= 3:
        cmd = sys.argv[1]
        if cmd == "add":
            offset = 1
            reload_existing = False
            if len(sys.argv) > 2 and sys.argv[2] == "--reload":
                offset = 2
                reload_existing = True
            if len(sys.argv) < offset + 4:
                print("Usage: python manage_machines.py add [--reload] <name> <user> <ip>")
                print("   eg: python manage_machines.py add aqc-99 aqc-99 172.16.18.99")
                print("   eg: python manage_machines.py add --reload aqc-51 aqc-51 172.16.18.127")
                pause()
                return
            add_machine(sys.argv[offset + 1], sys.argv[offset + 2], sys.argv[offset + 3], reload_existing)
        elif cmd == "remove":
            remove_machine(sys.argv[2])
        else:
            print(f"Unknown command: {cmd}")
            pause()
            return
        pause()
        return

    while True:
        print()
        print("=" * 50)
        print("  MACHINE MANAGER")
        print("=" * 50)
        print("  1. Add a machine")
        print("  2. Add/Reload a machine (re-download if exists)")
        print("  3. Remove a machine")
        print("  4. Exit")
        print("=" * 50)
        try:
            choice = input("  Choose an option (1-4): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye.")
            break

        if choice == "1" or choice == "2":
            reload_existing = (choice == "2")
            label = "Reload" if reload_existing else "Add"
            try:
                name = input(f"  Machine name (e.g. aqc-99): ").strip()
                user = input(f"  SSH user (e.g. aqc-99): ").strip()
                ip = input(f"  IP address (e.g. 172.16.18.99): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  Cancelled.")
                break
            if name and user and ip:
                add_machine(name, user, ip, reload_existing)
            else:
                print("  [!] All fields required.")
            pause_continue()

        elif choice == "3":
            try:
                name = input("  Machine name to remove (e.g. aqc-99): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  Cancelled.")
                break
            if name:
                try:
                    confirm = input(f"  Are you sure you want to remove '{name}'? (y/N): ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print("\n  Cancelled.")
                    break
                if confirm == "y":
                    remove_machine(name)
                else:
                    print("  Cancelled.")
            pause_continue()

        elif choice == "4":
            print("  Goodbye.")
            break

        else:
            print("  Invalid choice.")
            pause_continue()


if __name__ == "__main__":
    main()
