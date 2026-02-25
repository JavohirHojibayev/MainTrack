import logging
import sys
from app.core.esmo_client import EsmoClient
from app.core.config import settings
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debug_scrape")

def debug_scrape():
    client = EsmoClient(
        base_url=settings.ESMO_BASE_URL,
        username=settings.ESMO_USER,
        password=settings.ESMO_PASS
    )
    
    # Try standard form login first
    login_url = f"{client.base_url}personal/"
    payload = {
        "user_login": client.username,
        "user_pass": client.password,
        "submit": "1"
    }
    resp = client.session.post(login_url, data=payload)
    print(f"LOGIN_STATUS: {resp.status_code}")
    print(f"COOKIES: {client.session.cookies.get_dict()}")
    
    # Check if we are logged in by looking at content
    if "admin" in resp.text.lower() and "logout" in resp.text.lower():
        print("LOGIN_APPARENT_SUCCESS")
        client.is_logged_in = True
    else:
        # Try original method
        if not client.login():
            print("AJAX_LOGIN_FAILED")
            return
        else:
            print("AJAX_LOGIN_SUCCESS")

    # Access personal page to verify session
    resp = client.session.get(f"{client.base_url}personal/")
    print(f"PERSONAL_STATUS: {resp.status_code}")
    if "admin" in resp.text.lower():
        print("PERSONAL_PAGE_VERIFIED (Logged in)")
        # Find monitoring link
        soup = BeautifulSoup(resp.text, 'lxml')
        mon_link = soup.find('a', string=lambda t: t and 'МОНИТОРИНГ' in t)
        if mon_link:
            print(f"MONITOR_LINK_HREF: {mon_link.get('href')}")
            print(f"MONITOR_LINK_ATTRS: {mon_link.attrs}")
        else:
            # Try finding by icon or class if text match fails
            mon_link = soup.find('a', attrs={'title': 'МОНИТОРИНГ'}) or \
                       soup.find('a', attrs={'cmd': 'aspmo/no_cmd'})
            if mon_link:
                 print(f"MONITOR_LINK_FOUND_BY_ATTR: {mon_link.get('href')}")
            else:
                 print("MONITOR_LINK_NOT_FOUND")
    else:
        print("PERSONAL_PAGE_FAILED (Not logged in)")
        # Show a bit of HTML to see what's there
        print(f"HTML_SNIPPET: {resp.text[:500]}")

    # Try different monitor URLs
    urls = [
        f"{client.base_url}monitor/",
        f"{client.base_url}monitor/index.php",
        f"{client.base_url}monitor/monitor_ws.php"
    ]
    
    for mon_url in urls:
        print(f"TRying: {mon_url}")
        resp = client.session.get(mon_url)
        print(f"  STATUS: {resp.status_code}, LEN: {len(resp.text)}")
        if resp.status_code == 200 and "item" in resp.text:
             print(f"  SUCCESS! Found 'item' rows in {mon_url}")
             # Save this one
             with open("monitor_success.html", "w", encoding="utf-8") as f:
                 f.write(resp.text)
             break
        elif "Для авторизации" in resp.text:
             print(f"  FAILED: Redirected to login message in {mon_url}")
        else:
             print(f"  FAILED: No rows or unexpected content in {mon_url}")

if __name__ == "__main__":
    debug_scrape()
