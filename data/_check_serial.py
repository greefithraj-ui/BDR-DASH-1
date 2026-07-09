import json, os

archive_root = r'D:\BDR\DESTINATION\archive'
target_serial = 'RA-CH3-LFN-W1-AS08-0000006'
count = 0
for root, dirs, files in os.walk(archive_root):
    for fname in files:
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(root, fname)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                data = json.load(f)
        except:
            continue
        slots = data.get('slots', {})
        for sk, sv in slots.items():
            sn = (sv.get('serial_number') or '').strip()
            if sn == target_serial:
                print('FILE:', fpath)
                print('  saved_at:', data.get('saved_at',''))
                print('  battery_current:', sv.get('battery_current'))
                print('  state:', sv.get('state'))
                print('  completed_cycles:', sv.get('completed_cycles'))
                print('  total_cycles:', sv.get('total_cycles'))
                print('  cycle:', sv.get('cycle'))
                # Show all numeric fields
                for k, v in sv.items():
                    if isinstance(v, (int, float)) and v is not None:
                        print(f'  {k}: {v}')
                print()
                count += 1
                if count >= 10:
                    break
    if count >= 10:
        break

print(f'Total matches: {count}')
