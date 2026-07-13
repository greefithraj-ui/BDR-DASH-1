"""Part 4: Off-by-one investigation on bdr_state.cycle vs len(completed_cycles)."""
import sys, os, json
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
from postgres_db import get_connection, init_db
import psycopg2.extras

ARCHIVE_ROOT = Path(r"D:\BDR\DESTINATION\archive")
SERIALS = [
    "RA-CH3-LFK-W1-AG08-0000206",
    "RA-CH3-LFK-W1-AS07-0000141",
    "RA-CH2-IR3-W1-RT06-E83",
]


def find_raw_file(serial_lower):
    """Find the latest raw file for this serial."""
    best = None
    for machine_dir in ARCHIVE_ROOT.iterdir():
        if not machine_dir.is_dir():
            continue
        for fp in machine_dir.rglob("*.json"):
            try:
                text = fp.read_text("utf-8", errors="replace")
                if serial_lower not in text.lower():
                    continue
                data = json.loads(text)
                saved = data.get("saved_at", "")
                for slot_id, slot in data.get("slots", {}).items():
                    sn = (slot.get("serial_number") or "").strip().lower()
                    if sn == serial_lower:
                        if best is None or saved > best[1]:
                            best = (fp, saved, machine_dir.name, slot)
                        break
            except Exception:
                continue
    return best


def ring_status_row(serial):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM ring_status WHERE serial_number = %s", (serial,))
            r = cur.fetchone()
            return dict(r) if r else None
    finally:
        conn.close()


def main():
    init_db()
    for serial in SERIALS:
        sl = serial.lower()
        print(f"\n{'='*90}")
        print(f"  Off-by-one: {serial}")
        print(f"{'='*90}")

        result = find_raw_file(sl)
        if not result:
            print(f"  No raw file found")
            continue

        fp, saved, machine, slot = result
        bdr_state = slot.get("bdr_state") or {}
        bdr_data = slot.get("bdr_data") or {}
        completed_list = bdr_state.get("completed_cycles") or []

        print(f"  File: {fp}")
        print(f"  Machine: {machine}  saved_at: {saved}")
        print(f"  State: {slot.get('state')}")
        print(f"")
        print(f"  bdr_state.cycle:            {bdr_state.get('cycle')}")
        print(f"  bdr_data.final_cycle:       {bdr_data.get('final_cycle')}")
        print(f"  bdr_data.avg_bdr:           {bdr_data.get('avg_bdr')}")
        print(f"  len(completed_cycles):      {len(completed_list) if isinstance(completed_list, list) else completed_list}")
        print(f"  completed_cycles type:      {type(completed_list).__name__}")
        if isinstance(completed_list, list) and completed_list:
            print(f"  completed_cycles[0] keys:   {list(completed_list[0].keys()) if isinstance(completed_list[0], dict) else completed_list[0]}")
            print(f"  completed_cycles values:    {[(c.get('cycle'), c.get('bdr')) for c in completed_list if isinstance(c, dict)]}")

        # ring_status
        rs = ring_status_row(serial)
        if rs:
            print(f"")
            print(f"  ring_status stores:")
            print(f"    cycle = {rs.get('cycle')}")
            print(f"    avg_bdr = {rs.get('avg_bdr')}")
            print(f"    phase = {rs.get('phase')}")

        # Interpretation
        print(f"")
        print(f"  INTERPRETATION:")
        bdr_state_cycle = bdr_state.get("cycle")
        bdr_data_final = bdr_data.get("final_cycle")
        completed_len = len(completed_list) if isinstance(completed_list, list) else None
        print(f"    bdr_state.cycle ({bdr_state_cycle}) = current cycle NUMBER (1-indexed, e.g. cycle 6 means 6th cycle in progress)")
        print(f"    len(completed_cycles) ({completed_len}) = count of FINISHED cycles")
        print(f"    bdr_data.final_cycle ({bdr_data_final}) = cycle count at BDR test finalization")
        print(f"    ring_status.cycle stores: {'bdr_state.cycle' if rs and rs.get('cycle') == bdr_state_cycle else 'bdr_data.final_cycle' if rs and rs.get('cycle') == bdr_data_final else 'unknown'}")
        if bdr_state_cycle and completed_len is not None:
            print(f"    Difference: {bdr_state_cycle} - {completed_len} = {bdr_state_cycle - completed_len}")
            if bdr_state_cycle - completed_len == 1:
                print(f"    This is a SEMANTIC DIFFERENCE: cycle number vs completed count, NOT an off-by-one bug")
            elif bdr_state_cycle == completed_len:
                print(f"    These are equal for this serial")


if __name__ == "__main__":
    main()
