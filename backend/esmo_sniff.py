import json
import time
from playwright.sync_api import sync_playwright

def sniff_esmo_monitor_popup():
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

        print("Waiting for page load...")
        time.sleep(3)

        # 1. Catch Popup
        print("Clicking МОНИТОРИНГ and waiting for popup...")
        monitor_link = page.get_by_text("МОНИТОРИНГ", exact=True)
        
        if monitor_link.count() > 0:
            with context.expect_page() as new_page_info:
                monitor_link.click()
            
            popup_page = new_page_info.value
            popup_page.wait_for_load_state("networkidle")
            time.sleep(5)
            
            print(f"Captured Popup Page: {popup_page.url}")
            with open("esmo_monitor_popup.html", "w", encoding="utf-8") as f:
                f.write(popup_page.content())
            popup_page.screenshot(path="esmo_monitor_popup_view.png")
        else:
            print("MONITORING link not found!")

        browser.close()

if __name__ == "__main__":
    sniff_esmo_monitor_popup()
