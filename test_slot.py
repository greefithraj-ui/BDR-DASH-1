import json
with open('D:/BDR/DESTINATION/archive/aqc-23/2026-07-08/01-50-17.json', 'r') as f:
    data = json.load(f)
for k, v in data.get('slots', {}).items():
    if '12.04' in json.dumps(v):
        print(f"SLOT: {k}, SERIAL: {v.get('serial_number')}")
        print(json.dumps(v.get('bdr_state'), indent=2))
