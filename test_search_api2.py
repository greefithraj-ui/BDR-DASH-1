import requests
import json
try:
    res = requests.get('http://localhost:8000/api/bdr/search_old_data?serial_number=ra-ch3-lfk-w1-rt08-0000161')
    print(res.status_code)
    print(res.text[:500])
except Exception as e:
    print(e)
