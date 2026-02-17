
import requests
try:
    resp = requests.get("http://127.0.0.1:8000/api/v1/devices")
    print(f"Status: {resp.status_code}")
    print(resp.text[:1000])
except Exception as e:
    print(e)
