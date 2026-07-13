import requests
import json
try:
    res = requests.get('http://localhost:8000/api/old-data/search?serial=RA-CH3-LFK-W1-AG08-0000038')
    print(res.status_code)
    print(res.text[:500])
except Exception as e:
    print(e)
