import requests
from requests.auth import HTTPDigestAuth
import json
import sys
import os

# Add parent dir to path to import settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings

def test_fetch_users():
    try:
        devices = json.loads(settings.HIKVISION_DEVICES)
    except:
        print("Error parsing config")
        return

    if not devices:
        print("No devices")
        return

    device = devices[0]
    host = device.get("host")
    user = settings.HIKVISION_USER
    password = settings.HIKVISION_PASS
    
    print(f"Connecting to {host}...")
    
    url = f"http://{host}/ISAPI/AccessControl/UserInfo/Search?format=json"
    auth = HTTPDigestAuth(user, password)
    
    payload = {
        "UserInfoSearchCond": {
            "searchID": "test_search",
            "searchResultPosition": 0,
            "maxResults": 10
        }
    }
    
    try:
        resp = requests.post(url, json=payload, auth=auth, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            users = data.get("UserInfoSearch", {}).get("UserInfo", [])
            print(f"Found {len(users)} users (first 10):")
            for u in users:
                print(f" - {u.get('employeeNo')} : {u.get('name')}")
        else:
            print("Response:", resp.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_fetch_users()
