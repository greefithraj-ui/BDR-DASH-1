"""Deep scan: ALL files per machine for ground truth serial + off-by-one serials."""
import sys, os, json, mmap
from pathlib import Path

ARCHIVE_ROOT = Path(r"D:\BDR\DESTINATION\archive")


def search_all_files_for_serial(serial_lower):
    """Scan ALL JSON files across all machines for this serial. Returns {machine: [(fp, saved_at, slot_data)]}."""
    results = {}
    for machine_dir in sorted(ARCHIVE_ROOT.iterdir()):
        if not machine_dir.is_dir():
            continue
        machine_results = []
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
                        machine_results.append((str(fp), saved, slot_id, slot))
                        break
            except Exception:
                continue
        if machine_results:
            # Keep only the latest per machine
            machine_results.sort(key=lambda x: x[1], reverse=True)
            results[machine_dir.name] = machine_results[0]  # latest only
    return results


def main():
    serials = [
        ("RA-CH2-LFK-W1-MG07-0000106", "GROUND TRUTH"),
        ("RA-CH3-HF3-WB-AS09-0000111", "TARGET"),
    ]

    for serial, label in serials:
        sl = serial.lower()
        print(f"\n{'='*90}")
        print(f"  {label}: {serial} -- scanning ALL files per machine")
        print(f"{'='*90}")

        results = search_all_files_for_serial(sl)
        if not results:
            print(f"  NOT FOUND in any file on any machine")
            continue

        print(f"  Found on {len(results)} machine(s):")
        for m, (fp, saved, slot_id, slot) in sorted(results.items()):
            bdr_state = slot.get("bdr_state") or {}
            bdr_data = slot.get("bdr_data") or {}
            completed = bdr_state.get("completed_cycles") or []
            print(f"\n    {m}:")
            print(f"      file:     {fp}")
            print(f"      saved_at: {saved}")
            print(f"      state:    {slot.get('state')}")
            print(f"      bdr_state.cycle:       {bdr_state.get('cycle')}")
            print(f"      bdr_data.final_cycle:  {bdr_data.get('final_cycle')}")
            print(f"      len(completed_cycles): {len(completed) if isinstance(completed, list) else completed}")
            print(f"      bdr_data.avg_bdr:      {bdr_data.get('avg_bdr')}")
            print(f"      bdr_state.avg_bdr:     {bdr_state.get('avg_bdr')}")
            if isinstance(completed, list) and completed:
                print(f"      completed_cycles[0]:   {completed[0] if completed else 'empty'}")


if __name__ == "__main__":
    main()
