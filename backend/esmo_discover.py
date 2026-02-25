import socket
import ssl
import urllib.request
import base64
import json
import time

TARGET_IP = "192.168.8.10"
AUTH = b"Basic " + base64.b64encode(b"admin:QW1665gety")
PATHS_TO_CHECK = [
    "/cab/esmo_setting/terminal/",
    "/cab/api/",
    "/api/",
    "/api/v1/",
    "/api/terminals/",
    "/api/employees/",
    "/api/events/",
]

def test_http(ip, port, path, use_ssl=False):
    protocol = "https" if use_ssl else "http"
    url = f"{protocol}://{ip}:{port}{path}"
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url)
    req.add_header("Authorization", AUTH)
    req.add_header("Accept", "application/json")
    
    try:
        start = time.time()
        resp = urllib.request.urlopen(req, context=ctx, timeout=3)
        duration = time.time() - start
        
        status = resp.getcode()
        content_type = resp.getheader('Content-Type', '')
        
        body = b""
        if status in [200, 201, 401, 403]:
             body = resp.read(1000)
             
        return {
            "success": True,
            "url": url,
            "status": status,
            "content_type": content_type,
            "duration": round(duration, 2),
            "body": body.decode('utf-8', errors='replace')
        }
    except urllib.error.HTTPError as e:
        return {"success": False, "url": url, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"success": False, "url": url, "error": str(e)}

def main():
    print(f"--- Starting ESMO HTTP Discovery on {TARGET_IP} ---")
    
    print(f"\nTesting user-provided URL...")
    res = test_http(TARGET_IP, 443, "/cab/esmo_setting/terminal/", use_ssl=True)
    print(json.dumps(res, indent=2))

    print("\nFuzzing API paths on port 443...")
    for path in PATHS_TO_CHECK:
        res = test_http(TARGET_IP, 443, path, use_ssl=True)
        if res.get("success") or (res.get("error") and "HTTP" in res.get("error")):
             print(f"  -> {res['url']} : {res.get('status', res.get('error'))}")
             if res.get("status") == 200:
                 print(f"     Type: {res.get('content_type')}\n     Body preview: {res.get('body', '').strip()[:200]}")

if __name__ == "__main__":
    main()
