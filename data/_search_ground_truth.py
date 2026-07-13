"""Search specific machine dirs for ground truth serial - targeted scan."""
import sys, os, json, mmap
from pathlib import Path

ARCHIVE_ROOT = Path(r"D:\BDR\DESTINATION\archive")
SERIAL = "RA-CH2-LFK-W1-MG07-0000106"


def search_machine(machine_dir, serial_lower):
    """Search all files in a machine dir for the serial. Return latest match."""
    best = None
    for fp in machine_dir.rglob("*.json"):
        try:
            with open(fp, "rb") as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
                    if m.find(serial_lower.encode("utf-8")) == -1:
                        continue
            data = json.loads(fp.read_text("utf-8", errors="replace"))
            saved = data.get("saved_at", "")
            for slot_id, slot in data.get("slots", {}).items():
                sn = (slot.get("serial_number") or "").strip().lower()
                if sn == serial_lower:
                    if best is None or saved > best[0]:
                        best = (saved, str(fp), slot_id, slot)
        except Exception:
            continue
    return best


def main():
    sl = SERIAL.lower()
    print(f"Searching for {SERIAL} across all machines...")
    print(f"Scanning ALL files (not just latest)...\n")

    results = {}
    for machine_dir in sorted(ARCHIVE_ROOT.iterdir()):
        if not machine_dir.is_dir():
            continue
        result = search_machine(machine_dir, sl)
        if result:
            results[machine_dir.name] = result
            saved, fp, slot_id, slot = result
            bdr_state = slot.get("bdr_state") or {}
            bdr_data = slot.get("bdr_data") or {}
            completed = bdr_state.get("completed_cycles") or []
            print(f"FOUND on {machine_dir.name}:")
            print(f"  file:     {fp}")
            print(f"  saved_at: {saved}")
            print(f"  state:    {slot.get('state')}")
            print(f"  slot:     {slot_id}")
            print(f"  bdr_state.cycle:       {bdr_state.get('cycle')}")
            print(f"  bdr_data.final_cycle:  {bdr_data.get('final_cycle')}")
            print(f"  len(completed_cycles): {len(completed) if isinstance(completed, list) else completed}")
            print(f"  bdr_data.avg_bdr:      {bdr_data.get('avg_bdr')}")
            print(f"  ring_mac:              {slot.get('ring_mac')}")
            print()

    print(f"\nTotal machines found: {len(results)}")
    if not results:
        print("NOT FOUND on any machine")


if __name__ == "__main__":
    main()
