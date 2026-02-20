"""
ESMO Terminal Discovery Script
===============================
Bu skript ESMO terminallarini xavfsiz tekshiradi:
- Faqat GET so'rovlar (read-only, hech narsa o'zgartirmaydi)
- Port scanning (qaysi portlar ochiq)
- HTTP endpoint discovery (API mavjudligini tekshirish)

Ishlatish: python scripts/discover_esmo.py
"""

import socket
import json
import sys
from datetime import datetime

# requests kutubxonasi kerak
try:
    import requests
    from requests.auth import HTTPBasicAuth, HTTPDigestAuth
except ImportError:
    print("❌ 'requests' kutubxonasi kerak. O'rnating: pip install requests")
    sys.exit(1)


# ═══════════════════════════════════════════════════════
# ESMO terminallari ma'lumotlari (rasmdan olingan)
# ═══════════════════════════════════════════════════════
ESMO_DEVICES = [
    {"name": "TKM 1-terminal", "ip": "192.168.8.17", "serial": "SN020245001", "model": "MT-02"},
    {"name": "TKM 2-terminal", "ip": "192.168.8.18", "serial": "SN020245009", "model": "MT-02"},
    {"name": "TKM 3-terminal", "ip": "192.168.8.19", "serial": "SN020245002", "model": "MT"},
    {"name": "TKM 4-terminal", "ip": "192.168.8.20", "serial": "SN020245004", "model": "MT-02"},
]

# Tekshiriladigan portlar
COMMON_PORTS = [80, 443, 8080, 8443, 3000, 5000, 8000, 8888, 9090, 22, 21, 23, 502, 1433, 3306, 5432]

# Tekshiriladigan HTTP yo'llar (barcha GET — xavfsiz!)
COMMON_API_PATHS = [
    "/",
    "/api",
    "/api/v1",
    "/api/v1/status",
    "/api/v1/results",
    "/api/v1/events",
    "/api/v1/health",
    "/api/status",
    "/api/results",
    "/api/events",
    "/api/health",
    "/status",
    "/health",
    "/info",
    "/version",
    "/swagger",
    "/swagger-ui",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api-docs",
    # ESMO-specific guesses
    "/esmo",
    "/esmo/api",
    "/esmo/results",
    "/esmo/status",
    "/examination",
    "/examination/results",
    "/results",
    "/medical",
    "/medical/results",
    "/ISAPI/System/deviceInfo",  # Hikvision-style
    "/ISAPI/Event/notification/alertStream",
]


def check_port(ip: str, port: int, timeout: float = 1.5) -> bool:
    """Portni tekshirish (TCP connect)"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def check_http_endpoint(ip: str, port: int, path: str, timeout: float = 3) -> dict | None:
    """HTTP endpointni tekshirish (faqat GET — xavfsiz!)"""
    for scheme in ["http", "https"]:
        url = f"{scheme}://{ip}:{port}{path}"
        try:
            # Birinchi oddiy so'rov
            resp = requests.get(url, timeout=timeout, verify=False, allow_redirects=True)
            result = {
                "url": url,
                "status_code": resp.status_code,
                "content_type": resp.headers.get("Content-Type", ""),
                "server": resp.headers.get("Server", ""),
                "body_preview": resp.text[:500] if resp.text else "",
                "headers": dict(resp.headers),
            }

            # Agar 401 bo'lsa — auth kerakligini ko'rsatadi
            if resp.status_code == 401:
                result["auth_required"] = True
                result["www_authenticate"] = resp.headers.get("WWW-Authenticate", "")

            return result
        except requests.exceptions.SSLError:
            continue
        except requests.exceptions.ConnectionError:
            continue
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            continue
    return None


def scan_device(device: dict) -> dict:
    """Bitta ESMO terminalni to'liq tekshirish"""
    ip = device["ip"]
    name = device["name"]
    results = {
        "device": device,
        "timestamp": datetime.now().isoformat(),
        "ping_reachable": False,
        "open_ports": [],
        "http_endpoints": [],
    }

    print(f"\n{'='*60}")
    print(f"🔍 {name} ({ip}) tekshirilmoqda...")
    print(f"{'='*60}")

    # 1. Ping tekshirish
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((ip, 80))
        sock.close()
        # Try any port to check reachability
        for p in [80, 443, 8080]:
            if check_port(ip, p, 1):
                results["ping_reachable"] = True
                break
    except Exception:
        pass

    # 2. Port scanning
    print(f"  📡 Port scanning...")
    for port in COMMON_PORTS:
        if check_port(ip, port):
            results["open_ports"].append(port)
            print(f"  ✅ Port {port} — OCHIQ")
        else:
            print(f"  ⬜ Port {port} — yopiq")

    if not results["open_ports"]:
        print(f"  ❌ Hech qanday port ochiq emas! Terminal tarmoqqa ulanganligini tekshiring.")
        return results

    # 3. HTTP endpoint discovery
    http_ports = [p for p in results["open_ports"] if p in [80, 443, 8080, 8443, 3000, 5000, 8000, 8888, 9090]]
    if not http_ports:
        print(f"  ⚠️ HTTP portlar topilmadi.")
        return results

    print(f"\n  🌐 HTTP endpointlar tekshirilmoqda (portlar: {http_ports})...")
    for port in http_ports:
        for path in COMMON_API_PATHS:
            result = check_http_endpoint(ip, port, path)
            if result and result["status_code"] < 500:
                results["http_endpoints"].append(result)
                status = result["status_code"]
                emoji = "✅" if status == 200 else "🔑" if status == 401 else "🔶"
                print(f"  {emoji} {result['url']} — {status}")
                if result.get("server"):
                    print(f"      Server: {result['server']}")
                if result.get("content_type"):
                    print(f"      Type: {result['content_type']}")
                if status == 401:
                    print(f"      Auth: {result.get('www_authenticate', 'Kerak')}")
                if result.get("body_preview") and status == 200:
                    preview = result["body_preview"][:200].replace("\n", " ")
                    print(f"      Body: {preview}")

    return results


def main():
    print("=" * 60)
    print("🏥 ESMO Terminal Discovery Tool")
    print("📋 Faqat GET so'rovlar — ESMO'ga hech narsa yozilmaydi!")
    print("=" * 60)

    # SSL warninglarni o'chirish
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    all_results = []

    for device in ESMO_DEVICES:
        result = scan_device(device)
        all_results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("📊 XULOSA")
    print("=" * 60)

    for r in all_results:
        dev = r["device"]
        ports = r["open_ports"]
        endpoints = r["http_endpoints"]
        working = [e for e in endpoints if e["status_code"] == 200]
        auth_needed = [e for e in endpoints if e["status_code"] == 401]

        print(f"\n  {dev['name']} ({dev['ip']}):")
        print(f"    Ochiq portlar: {ports if ports else 'Yo`q ❌'}")
        print(f"    Ishlaydigan endpointlar: {len(working)}")
        print(f"    Auth kerak endpointlar: {len(auth_needed)}")

        if working:
            print(f"    ✅ Topilgan URL'lar:")
            for ep in working:
                print(f"       - {ep['url']}")

        if auth_needed:
            print(f"    🔑 Auth kerak:")
            for ep in auth_needed:
                print(f"       - {ep['url']} ({ep.get('www_authenticate', '')})")

    # Save results to file
    output_file = "scripts/esmo_discovery_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        # Remove large body previews for JSON
        clean_results = []
        for r in all_results:
            clean = {**r}
            clean["http_endpoints"] = [
                {k: v for k, v in ep.items() if k != "headers"}
                for ep in r["http_endpoints"]
            ]
            clean_results.append(clean)
        json.dump(clean_results, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n💾 Natijalar saqlandi: {output_file}")
    print("\n" + "=" * 60)
    print("📝 Keyingi qadam:")
    print("   Bu natijalarni menga (Antigravity) ko'rsating —")
    print("   men ESMO integratsiyasini yozaman!")
    print("=" * 60)


if __name__ == "__main__":
    main()
