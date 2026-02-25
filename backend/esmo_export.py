import json
import time
import os
from playwright.sync_api import sync_playwright

def download_esmo_csv():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--ignore-certificate-errors"])
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        print("Logging in to ESMO...")
        page.goto("https://192.168.8.10/cab/personal/", wait_until="networkidle")
        page.fill('input[name="user_login"]', "admin")
        page.fill('input[name="user_pass"]', "QW1665gety")
        page.click('button[type="submit"], input[type="submit"]')
        page.wait_for_load_state("networkidle")

        # Navigate to Journal
        journal_url = "https://192.168.8.10/cab/pp/journal/"
        print(f"Navigating to Journal: {journal_url}")
        page.goto(journal_url, wait_until="networkidle")
        time.sleep(2)

        # Trigger CSV download
        print("Triggering Excel CSV export...")
        with page.expect_download() as download_info:
            # We can trigger it by clicking the button with data-testid="csv" or text "Excel CSV"
            page.click('button[data-testid="csv"]')
        
        download = download_info.value
        path = "esmo_export.csv"
        download.save_as(path)
        print(f"Download completed: {path}")

        # Read and print first few lines of CSV
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                print("\n--- CSV Content Preview ---")
                for _ in range(20):
                    line = f.readline()
                    if not line: break
                    print(line.strip())
        
        browser.close()

if __name__ == "__main__":
    download_esmo_csv()
