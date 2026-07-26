# Legislation Explorer V2.1

**Release date:** 24 July 2026
**Version:** 2.1.0
**URL:** https://legislation.scriptkitty.yachts

---

## What's new in 2.1.1

### get_definition now returns full definition text

Previously returned only a pointer `{anchor, section}` — caller had to make a second `get_section` call and locate the right entry. Now resolves the anchor server-side and returns the actual definition body:

```json
{
  "term": "trading stock",
  "act": "itaa-1997",
  "section": "995-1",
  "anchor": "s995-1-trading-stock",
  "text": "trading stock has the meaning given by ...",
  "path": "/itaa-1997/s995-1#s995-1-trading-stock"
}
```

Also includes a `path` field for deep-linking. Truncated to 500 chars for manageable payloads.

**Version:** 2.1.1

---

## What's new in 2.1.0

### MCP — 9 tools (get_info added, case tools simplified)

The MCP server now exposes 9 tools over SSE transport:

- `search_cases` — Search tax cases by name, citation, or catchwords (returns weblinks)
- `search_legislation` — Search legislation sections by keyword
- `get_section` — Get full text of a legislation section
- `get_ruling` — Retrieve an ATO ruling by citation (accepts `TR 2020/1`, `TR_2020_1`, or `TR 2024/1`)
- `get_info` — Return server version, changelog, and tool list (no args)
- `list_acts`, `get_act_tree`, `get_definition` — Legislation browsing
- `get_rulings_for_section` — ATO rulings for a section

_Removed: `get_case` and `get_cases_for_section`. All case lookup is through `search_cases` — name search → weblink._

### Bug fixes

- **Ruling year fixed** — was always 0, now correctly parsed from citation for all ruling types
- **Citation format** — `get_ruling` now accepts `TR 2020/1`, `TR_2020_1`, or `TR 2024/1` (mixed spacing/slash formats)

### New `get_info` tool

Takes no arguments. Returns version, full changelog, and a list of all available MCP tools. Lets Claude Desktop self-discover what's available.

---

# Legislation Explorer V2.0

**Release date:** 24 July 2026
**Version:** 2.0.0
**URL:** https://legislation.scriptkitty.yachts

---

## What's new

### 6,700+ tax cases — searchable, browsable, expandable

Integrated tax case database across all 4 courts. Accessible from the act selector dropdown — "Tax Cases" mode renders the sidebar as a collapsible tree (Court → Year → Case). All cases are searchable by name, citation, or catchwords.

| Court | Cases |
|-------|-------|
| High Court (HCA) | 966 |
| Federal Court (FCA) | 1,834 |
| Full Federal Court (FCAFC) | 445 |
| AAT / ARTA | 3,456 |
| **Total** | **6,701** |

### Unified search across all categories

New search bar at the top of the main content pane. Searches every act, CCH guide, ATO ruling, and tax case simultaneously. Results grouped by category with counts:

- ITAA 1997, ITAA 1936, TAA 1953, GST Act
- Master Tax Guide, Master Tax Examples
- ATO Rulings, Tax Cases

### CCH Master Tax Guide & Examples — proper chapter titles

Backfilled 45 chapter titles from section_index into the Master Tax Guide tree (e.g. "01: Introduction to Australian Tax System"). Same for 12 chapters in Master Tax Examples. Sections inside chapters now show their titles too.

### TAA Schedule 1 — properly named and expandable

The "Part UNKNOWN" with empty title (which was Schedule 1 — Taxation Administration Act) is now named "Schedule 1 — Taxation Administration Act" with all 74 divisions visible and expandable in the sidebar tree.

### MCP Hall of Fame

Token creation now requires a name. Each MCP call is logged with a timestamp. Leaderboard at `/api/mcp-hall-of-fame` shows top callers across daily, weekly, monthly, and all-time windows. Scrolling banner at the top of the page shows the top 3. Click the 🏆 icon in the sidebar footer (after dismissing the banner) for the full modal with medal rankings.

### Monthly automated sync

New cases are ingested automatically on the 1st of every month:
1. Scrapes AustLII for new HCA, FCA, FCAFC, and ARTA judgments
2. Filters for tax-relevant cases
3. Extracts catchwords, numbered paragraphs, and full text
4. Stores in SQLite for MCP enrichment
5. Updates JSON files and restarts the server

### Frontend performance — code-split build

Initial bundle reduced from 507 KB to 170 KB (66% smaller). 11 lazy-loaded chunks load on demand: MarkdownRenderers (320 KB), SectionContent, TaxCaseDetail, MCPModal, ChangelogModal, HallOfFame, and more. Markdown parser (320 KB) no longer blocks initial paint.

### MCP — 8 tools (simplified case tools)

The MCP server exposes 8 tools over SSE transport:

- `search_cases` — Search tax cases by name, citation, or catchwords (returns weblinks)
- `search_legislation` — Search legislation sections by keyword
- `get_section` — Get full text of a legislation section
- `get_ruling` — Retrieve an ATO ruling by citation
- `list_acts`, `get_act_tree`, `get_definition` — Legislation browsing
- `get_rulings_for_section` — ATO rulings for a section

_Removed: `get_case` (was SQL-enriched case detail) and `get_cases_for_section` (section→case mapping). All case lookup is now through `search_cases` — name search → weblink._

Generate a token at **Settings → MCP** in the UI.

### API info endpoint

`GET /api/info` returns version, changelog, and all 19 available endpoints with descriptions.

---

## Deprecations

The following endpoints are deprecated but still operational:

- `GET /api/tax-cases/{court}` — Use `/api/tax-cases/search` instead
- `GET /api/tax-cases` — Use `/api/tax-cases/search` instead
- `GET /api/section-tax-cases/{act}/{section}` — Use `/api/tax-cases/search` instead

---

## Technical notes

- **Backend:** FastAPI + uvicorn on port 8765
- **Frontend:** React + TypeScript, built to `frontend/dist/`
- **Database:** SQLite (`mcp_tokens.db`, `search_index.db`)
- **Scraping:** curl_cffi (Chrome impersonation) — bypasses AustLII 403
- **MCP:** SSE transport with token authentication + call logging
- **Cron:** Monthly on 1st via `monthly_case_ingest.py`
- **Code-splitting:** Rollup manual chunks, 11 lazy-loaded components