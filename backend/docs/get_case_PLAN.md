# Plan: `get_case` MCP Tool Family for Legislation Explorer

## Problem

7,377 cases, 226,619 paragraphs in Postgres. Existing `search_cases` returns metadata-only from flat JSON. No way to access structured case content without dumping everything.

**Hard rule:** Never dump full text via MCP. `documents.content` can be 612K chars.

## Data Overview

| Table | Rows |
|-------|------|
| `cases` | 7,377 |
| `case_paragraphs` | 226,619 |
| Courts | HCA, FCA, FCAFC, AATA |
| Section types | DECISION (39%), ISSUE (18%), ORDERS (10%), CONCLUSION (8%), FACTS (8%), HELD (7%), BACKGROUND (2%), ANALYSIS (2%), REASONING (1%) |
| Para dist | Median 17/case, P90 53/case, Max 1,727/case |
| Para length | Median 453 chars, Max 85,431 chars |
| Content length | Mean ~44K chars, Max 612K chars |

## Proposed: 4 Tools

### Tool 1: `get_case` — Metadata + Structural Outline

No paragraph content. Always returns in < 2 KB.

**Input:**
- `citation` (required) — e.g. `[2024] HCA 1`
- `include_legislation_refs` (optional, default `false`) — if true, also returns the actual list of legislation sections the case references

**Returns:** citation, case_name, court, decision_date, judges, outcome, head_notes, paragraph_count, section-type breakdown (type → count + sequence range), cited_by_count, legislation_refs_count, download_urls (AustLII + court-specific), content_length

**SQL:** Two lightweight aggregate queries on `cases` + `case_paragraphs`. No content column touched.

### Tool 2: `get_case_paragraphs` — Paragraph Content on Demand

**Input:**
- `citation` (required)
- `section_types` (optional array, e.g. `["FACTS", "REASONING"]`)
- `paragraph_start` (optional integer, offset within filtered results)
- `paragraph_limit` (optional, default 50, **max 100**)
- `range_start` / `range_end` (optional integers, sequence_order range)

**Constraint:** At least one filter required — prevent accidental full-case dump.

**Returns:** Paragraphs with full content (content column from `case_paragraphs`, not `documents`). Plus `total_matching` + `truncated` flag.

**Safety:** Two hard caps — 100 paragraphs AND 50K chars total, whichever hits first.

**Note:** `range_start`/`range_end` let you navigate by sequence order (for reading front-to-back). `section_types` + `paragraph_start` let you jump to a specific section type (for targeted reading). Both can be combined.

### Tool 3: `search_case_paragraphs` — Full-Text Search Across Paragraphs

**Input:**
- `citation` (optional — if omitted, searches ALL 7,377 cases)
- `query` (required)
- `section_types` (optional array)
- `limit` (optional, default 10, max 30 for cross-case, max 100 for within-case)

**Returns:** Matching paragraphs with `ts_headline` snippets + `total_matches` count.

This is the most valuable legal research tool — "find all cases discussing 'capital gains'" across all cases, or "find where this judge discussed s 99B" within one case.

### Tool 4: `download_case` — Download Links (No Full Text via MCP)

**Purpose:** Give the user weblinks to download the full case text for offline research, rather than dumping it through MCP.

**Input:**
- `citation` (required)

**Returns:**
```json
{
  "citation": "[2024] HCA 1",
  "case_name": "Commissioner of Taxation v Example",
  "austlii_url": "https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/HCA/2024/1.html",
  "court_url": "https://www.hcourt.gov.au/...",
  "content_length": 245000,
  "paragraph_count": 214,
  "note": "Full text is available for download from AustLII or court website. MCP does not serve full text to avoid context overflow. Use get_case_paragraphs for structured access."
}
```

URLs generated from citation pattern: `https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/{COURT}/{YEAR}/{NUM}.html` plus court-specific primary URLs where available (HCA judgments page, FedCourt judgments).

## Implementation

**New file:** `backend/services/case_db_service.py`
Reuses `_sql()` / `_sql_dict()` from `tax_case_sql.py` (docker exec pattern).

**Modified:** `backend/mcp_server.py` — 4 new tool registrations + handlers.

## Migration

Once tested and deployed, mark standalone `cadena-knowledge-MCP` as deprecated and retire it. All its data lives in the same Postgres DB that legislation-explorer already accesses.

## Estimated Effort

~8-12 hours total across 4 tools.
