import json
from playwright.sync_api import sync_playwright

def list_esmo_links():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors"])
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        print("Logging in...")
        page.goto("https://192.168.8.10/cab/personal/", wait_until="networkidle")
        page.fill('input[name="user_login"]', "admin")
        page.fill('input[name="user_pass"]', "QW1665gety")
        page.click('button[type="submit"], input[type="submit"]')
        page.wait_for_load_state("networkidle")

        print("Listing all links on dashboard...")
        links = page.eval_on_selector_all('a', 'elements => elements.map(e => ({text: e.innerText.trim(), href: e.href}))')
        
        with open("esmo_links.json", "w", encoding="utf-8") as f:
            json.dump(links, f, indent=2, ensure_ascii=False)
            
        print(f"Found {len(links)} links.")
        browser.close()

if __name__ == "__main__":
    list_esmo_links()
