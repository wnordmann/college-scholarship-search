import os
import json
import time
import requests
import pandas as pd
from io import StringIO
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, Browser, Playwright, Error

# Load credentials
load_dotenv()
SERPER_KEY = os.getenv("serper_key")

# --- Constants ---
INPUT_CSV = Path("top_500_colleges.csv")
OUTPUT_DIR = Path("results_bot1")
BASE_QUERY = "automatic freshman merit scholarship academic grid 2026"


def safe_filename(name: str) -> str:
    """Sanitizes a string to be a valid filename."""
    # Adapted from safe_dirname in scraper.py
    cleaned = []
    for ch in name.strip():
        if ch.isalnum() or ch in (" ", "-", "_"):
            cleaned.append(ch)
        else:
            cleaned.append("_")
    # Replace spaces with underscores and remove trailing/leading underscores
    return "".join(cleaned).replace(" ", "_").strip("_") or "unknown_school"


def find_scholarship_url(school_name: str) -> str | None:
    """Uses Serper API to find the direct merit scholarship page."""
    print(f"🔍 Searching for {school_name}...")
    url = "https://google.serper.dev/search"
    query = f"{school_name} {BASE_QUERY}"

    payload = json.dumps({"q": query})
    headers = {'X-API-KEY': SERPER_KEY, 'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        results = response.json()
        if 'organic' in results and len(results['organic']) > 0:
            return results['organic'][0]['link']
    except requests.RequestException as e:
        print(f"   ❌ Search failed: {e}")
    return None


def scrape_merit_tables(page: Page, url: str) -> list[pd.DataFrame]:
    """Uses Playwright to render the page and Pandas to extract tables."""
    print(f"   🌐 Scraping: {url}")
    try:
        # Wait for network to be idle to ensure JavaScript tables load
        page.goto(url, wait_until="networkidle", timeout=60000)
        content = page.content()

        # Find all tables on the page
        tables = pd.read_html(StringIO(content))
        return tables
    except ValueError:
        # This is the specific error pandas raises when no tables are found.
        # It's not a failure of the scrape, just an absence of data.
        # The main loop will correctly report that no tables were found.
        return []
    except Error as e: # Catches Playwright-specific errors (e.g., navigation timeout)
        print(f"   ❌ Scrape failed: {e}")
        return []


def main() -> None:
    """Main execution function."""
    start_time = datetime.now()
    print(f"🚀 Starting scrape at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    if not SERPER_KEY:
        print("Error: SERPER_KEY not found in .env file.")
        return

    if not INPUT_CSV.exists():
        print(f"Error: Input file '{INPUT_CSV}' not found!")
        return

    schools_df = pd.read_csv(INPUT_CSV)
    OUTPUT_DIR.mkdir(exist_ok=True)

    # List to store reporting data for the summary
    report_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Main Loop
        for school_name in schools_df['School Name']:
            report_entry = {
                "school_name": school_name,
                "status": "Failure",
                "url_found": "N/A",
                "tables_saved": 0,
                "reason": "An unknown error occurred.",
            }

            if not isinstance(school_name, str) or not school_name.strip():
                report_entry["status"] = "Skipped"
                report_entry["reason"] = "Invalid or empty school name in CSV"
                report_data.append(report_entry)
                continue

            target_link = find_scholarship_url(school_name)

            if target_link:
                report_entry["url_found"] = target_link
                tables = scrape_merit_tables(page, target_link)

                if tables:
                    saved_count = 0
                    for i, table in enumerate(tables):
                        # A table is considered useful if it has at least 2 rows, 2 columns,
                        # and a minimum number of non-empty cells. This helps filter out
                        # small, empty, or UI-element tables like search boxes.
                        is_useful = (
                            table.shape[0] > 1 and
                            table.shape[1] > 1 and
                            table.count().sum() >= 4  # Require at least 4 data points
                        )
                        if is_useful:
                            fname = f"{safe_filename(school_name)}_table_{i}.csv"
                            output_path = OUTPUT_DIR / fname
                            table.to_csv(output_path, index=False)
                            saved_count += 1

                    report_entry["tables_saved"] = saved_count
                    if saved_count > 0:
                        report_entry["status"] = "Success"
                        report_entry["reason"] = f"Saved {saved_count} valid tables."
                        print(f"   ✅ Saved {saved_count} tables for {school_name}")
                    else:
                        report_entry["status"] = "Partial Success"
                        report_entry["reason"] = "URL scraped, but no suitable tables found."
                        print(f"   ⚠️ No suitable tables found for {school_name} at {target_link}")
                else:
                    report_entry["reason"] = "Could not scrape any tables from the URL."
                    print(f"   ⚠️ No tables found at {target_link}")
            else:
                report_entry["reason"] = "Could not find a scholarship URL via search."
                print(f"   ⚠️ No link found for {school_name}")

            report_data.append(report_entry)
            # Be a good citizen and sleep between requests
            time.sleep(2)

        browser.close()

    # Create and save the summary report
    report_df = None
    if report_data:
        report_df = pd.DataFrame(report_data)
        report_path = OUTPUT_DIR / "summary_report.csv"
        report_df.to_csv(report_path, index=False)
        print(f"\n📊 Summary report saved to {report_path}")

    end_time = datetime.now()
    running_time = end_time - start_time

    print("\n--- Run Summary ---")
    print(f"Start Time:   {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"End Time:     {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Running Time: {running_time}")

    if report_df is not None:
        total_checked = len(report_df)
        num_success = report_df['status'].eq('Success').sum()
        num_failed = total_checked - num_success

        print(f"Schools Checked: {total_checked}")
        print(f"Successes:       {num_success}")
        print(f"Failures:        {num_failed}")

    print("\nDone.")


if __name__ == "__main__":
    main()