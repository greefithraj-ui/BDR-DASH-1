import requests
import json
import time

time.sleep(2)
try:
    res = requests.get('http://localhost:8000/api/old-data/search/RA-CH3-LFK-W1-AG08-0000038')
    print(res.status_code)
    data = res.json()
    if 'results' in data and len(data['results']) > 0:
        print('latest avg_bdr:', data['results'][0]['avg_bdr'])
except Exception as e:
    print(e)
