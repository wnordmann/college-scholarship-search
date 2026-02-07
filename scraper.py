import csv
import json
import time
from pathlib import Path

import requests

INPUT_CSV = "sample_10.csv"
OUTPUT_ROOT = Path("scraped")
QUERY_SUFFIX = "mertic scholoarship grid 2026"


def safe_dirname(name: str) -> str:
    # Keep directory names readable while avoiding filesystem issues.
    cleaned = []
    for ch in name.strip():
        if ch.isalnum() or ch in (" ", "-", "_", "."):
            cleaned.append(ch)
        else:
            cleaned.append("_")
    out = "".join(cleaned).strip("_")
    return out or "unknown_school"


def fetch_search_page(query: str) -> requests.Response:
    url = "https://duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    return requests.get(url, params={"q": query}, headers=headers, timeout=30)


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            school = (row.get("School Name") or "").strip()
            if not school:
                continue

            query = f"{school} {QUERY_SUFFIX}"
            folder = OUTPUT_ROOT / safe_dirname(school)
            folder.mkdir(parents=True, exist_ok=True)

            try:
                resp = fetch_search_page(query)
            except Exception as exc:  # noqa: BLE001
                (folder / "error.txt").write_text(str(exc), encoding="utf-8")
                continue

            (folder / "query.txt").write_text(query + "\n", encoding="utf-8")
            (folder / "results.html").write_text(resp.text, encoding="utf-8")
            meta = {
                "query": query,
                "status_code": resp.status_code,
                "final_url": resp.url,
            }
            (folder / "meta.json").write_text(
                json.dumps(meta, indent=2), encoding="utf-8"
            )

            time.sleep(2)


if __name__ == "__main__":
    main()