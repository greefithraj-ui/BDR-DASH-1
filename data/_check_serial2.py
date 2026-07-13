import json, os, sys

archive_root = r'D:\BDR\DESTINATION\archive'
target_serial = 'RA-CH3-LFK-W1-RT08-0000114'

found = []
for root, dirs, files in os.walk(archive_root):
    for fname in files:
        if not fname.endswith('.json'): continue
        fpath = os.path.join(root, fname)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                data = json.load(f)
        except: continue
        slots = data.get('slots', {})
        for sk, sv in slots.items():
            sn = (sv.get('serial_number') or '').strip()
            if sn == target_serial:
                print(f"FILE: {fpath}")
                print(json.dumps(sv, indent=2))
                print(f"saved_at: {data.get('saved_at')}")
                found.append(fpath)
                if len(found) > 0:
                    sys.exit(0)
