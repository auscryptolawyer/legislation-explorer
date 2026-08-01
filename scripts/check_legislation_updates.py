#!/usr/bin/env python3
"""Check for legislation changes on legislation.gov.au OData API.

For each tracked act, queries the OData endpoint to get the current
compilation version and any amending acts. Compares against local
tree.json to detect changes.

Outputs JSON to stdout.
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from curl_cffi import requests as curl

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("check_legislation")

BASE_ODATA = "https://api.prod.legislation.gov.au/api/v1/odata"

# Act slugs → known FRBR URIs (api.prod endpoint)
TRACKED_ACTS = {
    "itaa-1997": {
        "name": "Income Tax Assessment Act 1997",
        "frbr_uri": "/au/leg/cth/consol_act/itaa1997332",
    },
    "itaa-1936": {
        "name": "Income Tax Assessment Act 1936",
        "frbr_uri": "/au/leg/cth/consol_act/itaa1936322",
    },
    "taa-1953": {
        "name": "Taxation Administration Act 1953",
        "frbr_uri": "/au/leg/cth/consol_act/taa1953236",
    },
    "gst-1999": {
        "name": "A New Tax System (Goods and Services Tax) Act 1999",
        "frbr_uri": "/au/leg/cth/consol_act/antstgsata1999486",
    },
    "fbt-1986": {
        "name": "Fringe Benefits Tax Assessment Act 1986",
        "frbr_uri": "/au/leg/cth/consol_act/fbtaa1986362",
    },
}

DATA_DIR = Path("/home/harrison/legislation-explorer/data")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def load_local_compilation(act_slug: str) -> dict:
    """Return the compilation_no and compilation_date from local tree.json."""
    tree_path = DATA_DIR / act_slug / "tree.json"
    if not tree_path.exists():
        return {}
    try:
        with open(tree_path) as f:
            tree = json.load(f)
        return {
            "compilation_no": tree.get("compilation_no"),
            "compilation_date": tree.get("compilation_date"),
        }
    except Exception as e:
        log.warning("Failed to read %s: %s", tree_path, e)
        return {}


def check_act_via_odata(act_slug: str, config: dict) -> dict:
    """Check compilation status via legislation.gov.au OData API.

    Uses the published OData endpoint with FRBR URI filtering.
    """
    frbr = config["frbr_uri"]
    act_name = config["name"]
    result = {
        "source": f"legislation_{act_slug}",
        "act_name": act_name,
        "has_changes": False,
        "local": load_local_compilation(act_slug),
        "remote": None,
        "amending_acts": [],
        "affected_sections": [],
        "error": None,
    }

    try:
        # Query OData for the latest compilation
        query_url = (
            f"{BASE_ODATA}/Compilations"
            f"?$filter=FRBRUri eq '{frbr}'"
            f"&$orderby=CompilationStartDate desc"
            f"&$top=5"
            f"&$expand=Amendments($expand=AmendingAct)"
        )
        log.info("Fetching %s", query_url)
        resp = curl.get(query_url, impersonate="chrome120", headers=HEADERS, timeout=30, verify=False)
        if resp.status_code != 200:
            result["error"] = f"OData HTTP {resp.status_code}"
            return result

        data = resp.json()
        compilations = data.get("value", data.get("d", {}).get("results", [data]))
        if not compilations:
            result["error"] = "No compilations found in OData response"
            return result

        # First compilation = latest
        latest = compilations[0]
        remote_comp = latest.get("CompilationNumber") or latest.get("Number") or ""
        remote_date = latest.get("CompilationStartDate") or latest.get("Date") or ""
        if isinstance(remote_date, str):
            remote_date = remote_date[:10]

        result["remote"] = {
            "compilation_no": remote_comp,
            "compilation_date": remote_date,
        }

        # Extract amending acts
        amendments = latest.get("Amendments", []) or latest.get("Amendments", {}).get("results", [])
        for am in amendments:
            amending = am.get("AmendingAct", {})
            if isinstance(amending, dict) and amending:
                am_name = amending.get("Title") or amending.get("Name") or "Unknown"
                am_id = amending.get("FRBRUri") or amending.get("Id") or ""
                result["amending_acts"].append({
                    "name": am_name,
                    "frbr_uri": am_id,
                })

        # Detect changes
        local = result["local"]
        remote = result["remote"]
        if local.get("compilation_no") != remote.get("compilation_no"):
            result["has_changes"] = True
            log.info(
                "%s: compilation changed local=%s remote=%s",
                act_slug,
                local.get("compilation_no"),
                remote.get("compilation_no"),
            )

        # If compilations differ but we couldn't get affected sections,
        # flag it so monthly_update can pass to the amendment parser
        if result["has_changes"] and not result["affected_sections"]:
            result["affected_sections"].append("(check amending acts — sections unknown)")

    except Exception as e:
        result["error"] = str(e)
        log.error("Error checking %s: %s", act_slug, e)

    return result


def check_act_via_scrape(act_slug: str, config: dict) -> dict:
    """Fallback: scrape the compilation details page for basic version info."""
    frbr = config["frbr_uri"]
    result = {
        "source": f"legislation_{act_slug}",
        "act_name": config["name"],
        "has_changes": False,
        "local": load_local_compilation(act_slug),
        "remote": None,
        "amending_acts": [],
        "affected_sections": [],
        "error": None,
    }
    try:
        # Try scraping the details HTML page
        # legislation.gov.au format: /Details/{id}
        act_id = frbr.rsplit("/", 1)[-1] if "/" in frbr else frbr
        url = f"https://www.legislation.gov.au/Details/{act_id}"
        resp = curl.get(url, impersonate="chrome120", headers=HEADERS, timeout=30, verify=False)
        if resp.status_code != 200:
            result["error"] = f"Scrape HTTP {resp.status_code}"
            return result

        # Look for compilation number in the page
        text = resp.text
        m = re.search(r"Compilation\s+(No\.?\s*)?(\d+)", text, re.IGNORECASE)
        if m:
            result["remote"] = {"compilation_no": m.group(2)}
            local = result["local"]
            if local.get("compilation_no") != m.group(2):
                result["has_changes"] = True

    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    start = time.time()
    results = []
    errors = []

    for slug, config in TRACKED_ACTS.items():
        r = check_act_via_odata(slug, config)
        if r.get("error") and "OData" in r["error"]:
            # Fallback to scrape
            log.warning("OData failed for %s, trying scrape fallback", slug)
            r = check_act_via_scrape(slug, config)
        results.append(r)
        if r.get("error"):
            errors.append({"source": slug, "error": r["error"]})

    # Summary
    total_changed = sum(1 for r in results if r.get("has_changes"))
    output = {
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(time.time() - start, 2),
        "acts_checked": len(results),
        "acts_changed": total_changed,
        "results": results,
        "errors": errors,
    }
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
