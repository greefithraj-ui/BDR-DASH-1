"""Targeted raw file search: only latest file per machine + mmap for speed."""
import sys, os, json, mmap
from pathlib import Path

ARCHIVE_ROOT = Path(r"D:\BDR\DESTINATION\archive")
SERIALS = [
    ("RA-CH2-LFK-W1-MG07-0000106", "ground_truth"),
    ("RA-CH3-HF3-WB-AS09-0000111", "target"),
    ("RA-CH3-LFK-W1-AG08-0000206", "off_by_one_candidate"),
    ("RA-CH3-LFK-W1-AS07-0000141", "off_by_one_candidate"),
    ("RA-CH2-IR3-W1-RT06-E83", "off_by_one_candidate"),
]


def get_latest_per_machine():
    """Get the latest JSON file path per machine directory (same as backfill)."""
    latest = {}
    for machine_dir in sorted(ARCHIVE_ROOT.iterdir()):
        if not machine_dir.is_dir():
            continue
        for date_dir in sorted(machine_dir.iterdir()):
            if not date_dir.is_dir():
                continue
            for json_file in sorted(date_dir.glob("*.json")):
                latest[machine_dir.name] = json_file
    return latest


def check_file_for_serial(fp, serial_lower):
    """Check if a file contains the serial. Uses mmap for speed."""
    try:
        with open(fp, "rb") as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
                if m.find(serial_lower.encode("utf-8")) == -1:
                    return None
        # Found it - parse for details
        data = json.loads(fp.read_text("utf-8", errors="replace"))
        saved = data.get("saved_at", "")
        for slot_id, slot in data.get("slots", {}).items():
            sn = (slot.get("serial_number") or "").strip().lower()
            if sn == serial_lower:
                return {"file": str(fp), "saved_at": saved, "slot": slot_id, "data": slot}
    except Exception:
        pass
    return None


def main():
    print("Building latest-file-per-machine index...")
    latest = get_latest_per_machine()
    print(f"Found {len(latest)} machines")

    for serial, label in SERIALS:
        sl = serial.lower()
        print(f"\n{'='*90}")
        print(f"  {label}: {serial}")
        print(f"{'='*90}")

        found = {}
        for machine, fp in sorted(latest.items()):
            result = check_file_for_serial(fp, sl)
            if result:
                found[machine] = result

        if not found:
            print(f"  NOT FOUND in latest file of any machine")
            # Also try rg on a smaller set
            continue

        print(f"  Found in {len(found)} machine(s) (latest files only):")
        for m, info in sorted(found.items()):
            slot = info["data"]
            bdr_state = slot.get("bdr_state") or {}
            bdr_data = slot.get("bdr_data") or {}
            completed = bdr_state.get("completed_cycles") or []
            print(f"    {m}: saved_at={info['saved_at']}  state={slot.get('state')}")
            print(f"      bdr_state.cycle={bdr_state.get('cycle')}  bdr_data.final_cycle={bdr_data.get('final_cycle')}  "
                  f"len(completed_cycles)={len(completed) if isinstance(completed, list) else completed}  "
                  f"avg_bdr(bdr_data)={bdr_data.get('avg_bdr')}  avg_bdr(bdr_state)={bdr_state.get('avg_bdr')}")


if __name__ == "__main__":
    main()
