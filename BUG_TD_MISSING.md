# Bug: TD (Tax Determination) rulings missing from ruling list

**Severity:** Medium  
**Area:** Data ingestion pipeline  
**Status:** Needs investigation

## Problem

Only 40 TD files exist in `/home/harrison/projects/cadena-knowledge-MCP/data/rulings/` (RULING_DIR). There should be hundreds — TDs have been issued since the early 1990s.

The `ato_rulings/td/` directory only has a single PDF (`td2024-001.pdf`) in a `2024/` subfolder. No TD `.txt` files exist there.

## Data sources

- **Primary:** `RULING_DIR` → `/home/harrison/projects/cadena-knowledge-MCP/data/rulings/` — 40 TD `.txt` files
- **Secondary:** `ATO_RULING_DIR/td/` → `/home/harrison/projects/cadena-knowledge-MCP/data/ato_rulings/td/` — 1 PDF in `2024/` subfolder

## Possible causes

1. TD scraping/extraction pipeline never ran for TDs (unlike TR, PCG, PS LA which have their own subdirectories in `ato_rulings/`)
2. TD files were only partially ingested into the old cadena-knowledge-MCP project
3. The `ato_rulings/td/` scraper only handles 2024 PDFs; earlier years were never extracted

## Fix needed

Extend the ATO rulings ingestion pipeline to scrape TD files from the ATO website (or bulk extract from the existing PDFs) and convert them to `.txt` format in `RULING_DIR`.