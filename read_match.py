import json
with open('D:/BDR/DESTINATION/archive/aqc-23/2026-07-08/01-50-17.json', 'r') as fd:
    data = json.load(fd)
    for k, v in data.get('slots', {}).items():
        if '0000038' in str(v.get('serial_number')):
            print('SERIAL:', v.get('serial_number'))
            print('STATE:', v.get('state'))
            print(json.dumps(v.get('bdr_state'), indent=2))
