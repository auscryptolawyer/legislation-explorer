#!/usr/bin/env python3
"""Download full case text from AustLII for all tax cases in the database.

Saves the raw HTML content to a local directory so it can be served as
direct download via the MCP download_case tool, or re-ingested with
proper paragraph segmentation.

Usage:
    python3 scripts/download_case_texts.py                          # download all missing cases
    python3 scripts/download_case_texts.py --citation "[2016] HCA 45"  # download a specific case
    python3 scripts/download_case_texts.py --dry-run                  # show what would be downloaded
    python3 scripts/download_case_texts.py --limit 10                # download first 10 missing

Output: Saves to data/case_texts/{citation}.html (or .txt)
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

from curl_cffi import requests as curl

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger(__name__)

# Config
DATA_DIR = Path(os.environ.get("DATA_DIR", "/home/harrison/legislation-explorer/data"))
CASE_TEXT_DIR = DATA_DIR / "case_texts"
CASE_DATA_DIR = Path(os.environ.get("CASE_DIR", "/home/harrison/projects/asic-scraper/cases"))
DELAY = 1.5  # seconds between requests

# AustLII URL pattern
AUSTLII_CASE = "https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/{court}/{year}/{num}.html"

# Citation regex
CITATION_RE = re.compile(r"\[(\d+)\]\s+(\w+)\s+(\d+)")


def get_all_citations() -> list[dict]:
    """Get all case citations from the tax case JSON files."""
    citations = []
    for court_key, court_label in [
        ("hca", "HCA"), ("fca", "FCA"), ("fcafc", "FCAFC"), ("aata", "AATA"),
    ]:
        path = DATA_DIR / f"{court_key}_tax_cases.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for case in data if isinstance(data, list) else data.get("results", []):
            citation = case.get("citation", "")
            m = CITATION_RE.match(citation)
            if m:
                citations.append({
                    "citation": citation,
                    "court": m.group(2),
                    "year": m.group(1),
                    "num": m.group(3),
                    "case_name": case.get("case_name", case.get("title", "")),
                })
    return citations


def get_existing_downloads() -> set[str]:
    """Return set of already-downloaded case citations, using the same format as save_case()."""
    if not CASE_TEXT_DIR.exists():
        return set()
    existing = set()
    for f in CASE_TEXT_DIR.glob("*.html"):
        # Reconstruct the original citation: 2002_HCA_18 -> [2002] HCA 18
        parts = f.stem.split("_", 2)
        if len(parts) == 3:
            citation = f"[{parts[0]}] {parts[1]} {parts[2]}"
            existing.add(citation)
    for f in CASE_TEXT_DIR.glob("*.txt"):
        parts = f.stem.split("_", 2)
        if len(parts) == 3:
            citation = f"[{parts[0]}] {parts[1]} {parts[2]}"
            existing.add(citation)
    return existing


def download_case(citation: str, court: str, year: str, num: str) -> str | None:
    """Download a case from AustLII using curl_cffi Chrome impersonation."""
    url = AUSTLII_CASE.format(court=court, year=year, num=num)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-AU,en;q=0.9",
    }
    try:
        resp = curl.get(url, impersonate="chrome120", headers=headers, timeout=30, verify=False)
        if resp.status_code == 200:
            return resp.text
        log.warning(f"HTTP {resp.status_code} for {citation} ({url})")
    except Exception as e:
        log.error(f"Failed to download {citation}: {e}")
    return None


def save_case(citation: str, html: str) -> Path:
    """Save the case HTML to CASE_TEXT_DIR."""
    CASE_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    # Sanitize citation for filename
    safe_name = citation.replace("[", "").replace("]", "").replace(" ", "_")
    path = CASE_TEXT_DIR / f"{safe_name}.html"
    path.write_text(html, encoding="utf-8")
    log.info(f"Saved {citation} ({len(html):,} chars)")
    return path


def main():
    parser = argparse.ArgumentParser(description="Download case texts from AustLII")
    parser.add_argument("--citation", type=str, help="Download a specific case")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded")
    parser.add_argument("--limit", type=int, default=0, help="Max cases to download")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay between requests")
    args = parser.parse_args()

    if args.citation:
        m = CITATION_RE.match(args.citation)
        if not m:
            log.error(f"Invalid citation: {args.citation}")
            sys.exit(1)
        cases = [{"citation": args.citation, "court": m.group(2),
                   "year": m.group(1), "num": m.group(3)}]
    else:
        cases = get_all_citations()

    existing = get_existing_downloads()
    missing = [c for c in cases if c["citation"] not in existing]
    log.info(f"Total cases: {len(cases)}, Already downloaded: {len(existing)}, Missing: {len(missing)}")

    if args.dry_run:
        log.info(f"Would download {len(missing)} cases")
        for c in missing[:10]:
            log.info(f"  {c['citation']} — {c.get('case_name', '')[:60]}")
        if len(missing) > 10:
            log.info(f"  ... and {len(missing) - 10} more")
        return

    if args.limit:
        missing = missing[:args.limit]

    downloaded = 0
    failed = 0

    for case in missing:
        html = download_case(case["citation"], case["court"],
                             case["year"], case["num"])
        if html:
            save_case(case["citation"], html)
            downloaded += 1
        else:
            failed += 1
        if args.limit and downloaded >= args.limit:
            break
        time.sleep(args.delay)

    log.info(f"Downloaded {downloaded} cases, {failed} failed")


if __name__ == "__main__":
    main()