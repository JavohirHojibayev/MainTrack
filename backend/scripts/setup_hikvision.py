import sys
import os
import requests
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings

def setup_http_listening():
    # Parse devices from config
    import json
    try:
        devices = json.loads(settings.HIKVISION_DEVICES)
    except:
        print("Error parsing HIKVISION_DEVICES from .env")
        return

    if not devices:
        print("No devices configured in .env")
        return

    print(f"Found {len(devices)} devices to configure.")

    # Target server IP (this computer's IP)
    server_ip = "192.168.0.3"
    server_port = "8000"
    server_url = "/api/v1/hikvision/webhook"

    for device in devices:
        host = device.get("host")
        name = device.get("name", host)
        user = settings.HIKVISION_USER
        password = settings.HIKVISION_PASS

        print(f"\n--------------------------------------------------")
        print(f"Configuring device: {name} ({host})...")

        base_url = f"http://{host}/ISAPI/Event/notification/httpHosts"
        auth = HTTPDigestAuth(user, password)

        try:
            # 1. GET current config (Check connectivity)
            print(f"  [{name}] Check connectivity...")
            resp = requests.get(base_url, auth=auth, timeout=5)
            resp.raise_for_status()
            print(f"  [{name}] Connection OK.")
        except Exception as e:
            print(f"  [{name}] SKIPPING: Could not connect or auth failed. Error: {e}")
            continue

        # 2. Construct XML for PUT
        xml_poyload = f"""<?xml version="1.0" encoding="UTF-8"?>
<HttpHostNotificationList version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
    <HttpHostNotification>
        <id>1</id>
        <url>{server_url}</url>
        <protocolType>HTTP</protocolType>
        <parameterFormatType>XML</parameterFormatType>
        <addressingFormatType>ipaddress</addressingFormatType>
        <ipAddress>{server_ip}</ipAddress>
        <portNo>{server_port}</portNo>
        <httpAuthenticationMethod>none</httpAuthenticationMethod>
        <anprImageUploading>true</anprImageUploading>
        <eventUploading>true</eventUploading>
    </HttpHostNotification>
</HttpHostNotificationList>
"""

        print(f"  [{name}] Uploading configuration...")
        try:
            resp = requests.put(base_url, data=xml_poyload, auth=auth, timeout=10)
            
            if resp.status_code == 200:
                print(f"  [{name}] SUCCESS! Configuration updated.")
            else:
                print(f"  [{name}] FAILED. Status: {resp.status_code}. Body: {resp.text}")
        except Exception as e:
            print(f"  [{name}] Error putting config: {e}")
            
    print("\n--------------------------------------------------")
    print("All devices processed.")
    print("Please reboot updated devices via iVMS for changes to take effect.")

if __name__ == "__main__":
    setup_http_listening()
