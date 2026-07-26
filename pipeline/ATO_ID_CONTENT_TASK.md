# ATO ID Content Fetcher — Task for Kimi Code

## Problem

We have 5,931 ATO ID (Interpretative Decision) placeholder files at:
`/home/harrison/projects/cadena-knowledge-MCP/data/rulings/AID_{year}_{num}.txt`

Each file is just a header — no actual document content. We need the full text from the ATO legal database.

## What Works

- `curl_cffi` (Chrome impersonation) successfully bypasses Akamai on `ato.gov.au`
- The PDF endpoint exists but only returns a cover page title
- The real content is in the ATO's jQuery SPA, loaded via XHR to TeraText API

## The SPA Architecture

The legal database at https://www.ato.gov.au/single-page-applications/legaldatabase is a DurandalJS (Knockout) SPA. The API endpoint is:

```
/API/v1/law/lawservices/
```

This is a **TeraText** database API. Direct calls to it return "Found load balance testing" — the load balancer blocks raw API access.

When accessed via `curl_cffi` with Chrome impersonation, the page at `https://www.ato.gov.au/law/view/document?docid=AID/AID{year}{num}/00001` returns the HTML shell (SPA bootstrap). The document content is loaded client-side via JavaScript XHR.

## Approach Options

### Option A: Reverse-engineer the TeraText API
Find the exact request format (POST body, headers, parameters) that the SPA sends to `/API/v1/law/lawservices/GetDocument` and replicate it with `curl_cffi`. This might need specific cookies, headers, or a POST body format.

### Option B: Headless browser with stealth
Playwright headless Chrome gets blocked by Akamai ("Access Denied"). Fix:
- Use undetected-chromedriver, playwright-stealth, or puppeteer-extra-plugin-stealth
- Or pipe curl_cffi's session cookies into Playwright

### Option C: Screenshot + OCR
Last resort — render via browser, screenshot, OCR. Not recommended.

## Files

- Placeholder dir: `/home/harrison/projects/cadena-knowledge-MCP/data/rulings/`
- Existing scraper (for reference): `/home/harrison/legislation-explorer/pipeline/scrape_ato_ids.py`
- Existing (broken) content fetcher: `/home/harrison/legislation-explorer/pipeline/fetch_ato_id_content.py`
- Backend rulings loader: `/home/harrison/legislation-explorer/backend/services/data_loader.py`

## Requirements

1. Fetch full document text for each ATO ID (2001-2016, 5,931 files)
2. Write content to the existing `.txt` files (replace placeholder, keep header)
3. Sequential requests to avoid rate limiting (~2 rps)
4. Resume capability (skip files with >100 chars content)
5. Handle withdrawn docs (they still have content)

## Test URLs

- Existing: `https://www.ato.gov.au/law/view/document?docid=AID/AID201050/00001` → returns SPA shell via curl_cffi
- PDF (cover only): `https://www.ato.gov.au/law/view/pdf?docid=AID/AID201050/00001`
