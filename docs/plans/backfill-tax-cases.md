# Backfill Tax Cases Plan

**Goal:** Backfill historical tax cases for HCA (1903-1997), FCA (1977-2001), and FCAFC (2002-2015) from AustLII, then merge with existing modern data.

**Approach:** AustLII provides year-by-year directory listings at predictable URLs (`/au/cases/cth/{COURT}/{YEAR}/`) accessible via curl_cffi. Each page lists all judgments for that year with full citations. We scrape each year, filter tax cases by keyword, deduplicate against existing data, and produce merged JSON files.

**Total pages to scrape:** ~160 (HCA 95 years + FCA 25 years + FCAFC 14 years)

**Tech:** curl_cffi (Chrome impersonation), Python stdlib (no new deps), keyword filtering

---

### Task 1: Build the AustLII tax case harvester script

**Objective:** Create a self-contained Python script that scrapes year-by-year pages from AustLII for a given court, identifies tax cases by keyword matching, and outputs the filtered cases plus stats.

**Files:**
- Create: `/home/harrison/scripts/austlii_tax_harvester.py`
- Output: `hca_tax_austlii.json`, `fca_tax_austlii.json`, `fcafc_tax_austlii.json`

**Script design (key points):**
- Input: court code (`HCA`, `FCA`, `FCAFC`), year range (start to end)
- Scrapes each year at `https://www.austlii.edu.au/au/cases/cth/{COURT}/{YEAR}/`
- Uses `curl_cffi.requests` with `impersonate='chrome124'`
- Extracts all case links: format `<a href="/cgi-bin/viewdoc/.../{YEAR}/{N}.html">Title [YEAR] COURT N; (YEAR) VOLUME CLR PAGE (Date)</a>`
- Filters tax cases using keyword matching (same keywords as the existing HCA filter, plus additional historical terms like "income tax assessment", "super tax", "war tax", "probate duty", "estate duty", "gift duty", "sales tax")
- Extracts: citation, title, year
- Handles pagination (some years may have multiple pages — check for `startat=` links)
- Outputs JSON array
- Prints stats: total scraped years, cases per year, tax cases found

**Keyword list for tax filtering:**
```python
tax_keywords = [
    'commissioner of taxation', 'deputy commissioner', 'federal commissioner of taxation',
    'commissioner of taxes', 'commissioner of state taxation', 'chief commissioner of state revenue',
    'taxation', 'income tax', 'capital gains', 'goods and services', 'gst', 'fringe benefits',
    'withholding', 'deduction', 'taxable', 'assessable', 'royalty', 'stamp duty', 'land tax',
    'payroll tax', 'excise', 'taxpayer', 'superannuation guarantee',
    'income tax assessment', 'super tax', 'war tax', 'probate duty', 'estate duty',
    'gift duty', 'sales tax', 'pay-roll tax', 'land tax assessment',
    'tax agent', 'tax (assessment', 'tax refund', 'tax file number',
    'commissioner of superannuation',
]
```

**Output format:**
```json
{
  "court": "HCA",
  "source": "austlii",
  "year_range": {"from": 1903, "to": 1997},
  "total_cases_scraped": 5000,
  "tax_cases_found": 85,
  "cases": [
    {
      "title": "Federal Commissioner of Taxation v Dalco",
      "citation": "[1990] HCA 3; (1990) 168 CLR 614",
      "year": 1990,
      "austlii_url": "/cgi-bin/viewdoc/au/cases/cth/HCA/1990/3.html"
    },
    ...
  ]
}
```

---

### Task 2: Harvest HCA pre-1998 tax cases

**Objective:** Run the script for HCA from 1903 to 1997. Expect roughly 80-100 tax cases across 95 years.

**Command:**
```bash
python3 scripts/austlii_tax_harvester.py --court HCA --from 1903 --to 1997 --output hca_tax_austlii.json
```

**Expected output:** ~5,000 total cases scraped, ~85 tax cases identified.
**Estimated time:** ~5 minutes (95 pages at ~3 seconds each).

**Verification:** Check year distribution spans 1903-1997 (no gaps). Spot-check known tax cases from memory:
- *Commissioner of Taxation v The Executor Trustee and Agency Company of South Australia Ltd* (1938) — estate duty
- *Federal Commissioner of Taxation v Munro* (1926) — income tax assessment
- *Commissioner of Taxation v McPhail* (1968) — tax deduction

---

### Task 3: Harvest FCA pre-2002 tax cases

**Objective:** Run the script for FCA from 1977 to 2001.

**Command:**
```bash
python3 scripts/austlii_tax_harvester.py --court FCA --from 1977 --to 2001 --output fca_tax_austlii.json
```

**Expected output:** ~3,000 total cases scraped, ~120 tax cases identified.
**Estimated time:** ~1.5 minutes (25 pages).

**Verification:** Check year distribution. Tax cases should start appearing from 1977 onward.

---

### Task 4: Harvest FCAFC pre-2016 tax cases

**Objective:** Run the script for FCAFC from 2002 to 2015.

**Command:**
```bash
python3 scripts/austlii_tax_harvester.py --court FCAFC --from 2002 --to 2015 --output fcafc_tax_austlii.json
```

**Expected output:** ~1,500 total cases scraped, ~80 tax cases identified.
**Estimated time:** ~1 minute (14 pages).

---

### Task 5: Build merge & deduplication script

**Objective:** Create a script that merges the new AustLII data with existing modern data, deduplicating by citation.

**Command:**
```bash
python3 scripts/merge_tax_cases.py
```

**Logic:**
1. Load existing modern data (`data/hca_tax_cases.json`, etc.)
2. Load AustLII backfill data
3. Build a set of existing citations
4. Append only new citations from AustLII data
5. Sort by year descending, then citation number descending
6. Write merged data back to `data/hca_tax_cases.json`, etc.
7. Print stats:
   - "HCA: 83 existing + 85 new = 168 total"
   - "FCA: 438 existing + 120 new = 558 total"
   - "FCAFC: 153 existing + 80 new = 233 total"

---

### Task 6: Restart backend & verify

**Objective:** Restart the legislation-explorer service and verify all three endpoints return the merged data.

**Command:**
```bash
systemctl --user restart legislation-explorer
```

**Verification:**
```bash
curl -s http://localhost:8765/api/tax-cases | python3 -m json.tool
```

Check:
- HCA: 28 existing years (1998-2026) + ~60 new years (1903-1997)
- FCA: 13 existing years (2002-2026) + 25 new years (1977-2001)
- FCAFC: 11 existing years (2016-2026) + 14 new years (2002-2015)

---

### Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| AustLII rate limiting | Add 1-2s delay between requests |
| Cloudflare challenge on some pages | curl_cffi Chrome impersonation; fallback to retry with different impersonation |
| Year page has sub-pages (pagination) | Script checks for `startat=` links and iterates |
| Some cases use non-standard citation format | Use regex that matches `[YYYY] COURT N` or `(YYYY) VOLUME CLR` patterns |
| AustLII changes URL structure | Script logs raw response if regex finds 0 cases in a year that should have cases |

---

### Summary

| Dataset | Existing | Backfill | Total | Years |
|---------|----------|----------|-------|-------|
| HCA | 83 (1998-2026) | ~85 (1903-1997) | ~168 | 124 |
| FCA | 438 (2002-2026) | ~120 (1977-2001) | ~558 | 50 |
| FCAFC | 153 (2016-2026) | ~80 (2002-2015) | ~233 | 25 |

**Total tax cases after backfill:** ~960 (up from 674)
