"""Part 3: Raw file scan for specific serials. Uses rg (ripgrep) for speed."""
import sys, os, json, subprocess
from pathlib import Path

ARCHIVE_ROOT = Path(r"D:\BDR\DESTINATION\archive")
SERIALS = [
    "RA-CH3-HF3-WB-AS09-0000111",
    "RA-CH2-LFK-W1-MG07-0000106",
]


def find_in_raw_files(serial_lower):
    """Use ripgrep to find files containing the serial, then parse the latest per machine."""
    results = {}
    # Use rg to find files containing the serial (much faster than Python scan)
    try:
        proc = subprocess.run(
            ["rg", "-l", "--ignore-case", serial_lower, str(ARCHIVE_ROOT)],
            capture_output=True, text=True, timeout=60
        )
        files = [Path(f) for f in proc.stdout.strip().split("\n") if f]
    except Exception:
        # Fallback: glob and check
        files = []
        for f in ARCHIVE_ROOT.rglob("*.json"):
            try:
                if serial_lower in f.read_text("utf-8", errors="replace").lower():
                    files.append(f)
            except Exception:
                continue

    for fp in files:
        try:
            data = json.loads(fp.read_text("utf-8", errors="replace"))
            saved = data.get("saved_at", "")
            machine = fp.parent.parent.name
            for slot_id, slot in data.get("slots", {}).items():
                sn = (slot.get("serial_number") or "").strip().lower()
                if sn == serial_lower:
                    if machine not in results or saved > results[machine][1]:
                        results[machine] = (str(fp), saved)
                    break
        except Exception:
            continue
    return results


def main():
    for serial in SERIALS:
        sl = serial.lower()
        print(f"\n{'='*90}")
        print(f"  Raw file scan: {serial}")
        print(f"{'='*90}")
        results = find_in_raw_files(sl)
        if not results:
            print(f"  NOT FOUND in any raw file")
            continue
        print(f"  Found in {len(results)} machine(s):")
        for m, (fp, saved) in sorted(results.items()):
            print(f"    {m}: saved_at={saved}")
            print(f"      {fp}")


if __name__ == "__main__":
    main()
