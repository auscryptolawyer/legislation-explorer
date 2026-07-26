# Plan: `get_case` MCP Tool(s) for Legislation Explorer

## Status: Proposed — July 2026

---

## 1. Problem Statement

The Postgres DB (`cadena_knowledge`) has **7,377 cases** with **226,619 paragraphs**. The existing `search_cases` MCP tool searches flat JSON files (metadata only) and returns brief case summaries with links. There is **no way** for an LLM agent to retrieve structured case content without:

- Pulling all paragraphs at once (the old `get_case_sql_data()` in `tax_case_sql.py` fetches every paragraph, limited to 500-char previews, plus chunks — too heavy for large cases).
- Querying the docs table directly (full document text, potentially enormous).

Some cases have **1,727 paragraphs** (max). Median is 17 paragraphs, P90 is 53. Even the median case's full text could be 25K+ chars across paragraphs; a 1,727-paragraph case would be unwieldy.

## 2. Database Overview

### Key Tables

| Table | Rows | Purpose |
|-------|------|---------|
| `cases` | 7,377 | Metadata: citation, case_name, court, decision_date, judges, outcome, head_notes (jsonb), related_provisions, related_rulings |
| `case_paragraphs` | 226,619 | Structured paragraph content with `section_type` classification |
| `documents` | ~7K+ | Full raw text (avoid direct access — too large) |
| `case_citations` | variable | Cross-case citation links with context |
| `case_legislation_refs` | variable | Case-to-legislation-section links |

### Cases Table Columns

`id` (uuid PK), `document_id` (FK→documents), `citation`, `case_name`, `court`, `decision_date`, `judges` (text[]), `outcome`, `related_provisions` (text[]), `related_rulings` (text[]), `head_notes` (jsonb)

### Case Paragraphs Columns

`id` (uuid PK), `case_id` (FK→cases), `paragraph_number` (int), `paragraph_label`, `section_type`, `content` (text), `sequence_order` (int)

Indexes: `idx_case_paragraphs_case_id`, `idx_case_paragraphs_section`, `idx_case_paragraphs_sequence` (case_id, sequence_order), `idx_case_paragraphs_content_fts` (GIN on content)

### Section Types (9 distinct values)

| Section Type | Count | % of Total |
|-------------|-------|-----------|
| DECISION | 89,394 | 39.4% |
| ISSUE | 41,383 | 18.3% |
| ORDERS | 22,605 | 10.0% |
| CONCLUSION | 19,125 | 8.4% |
| FACTS | 17,285 | 7.6% |
| HELD | 16,407 | 7.2% |
| BACKGROUND | 4,715 | 2.1% |
| ANALYSIS | 3,838 | 1.7% |
| REASONING | 3,059 | 1.3% |

### Paragraph Size Distribution

- **Median content length:** 453 chars
- **Average content length:** 1,364 chars
- **Max content length:** 85,431 chars (a single paragraph)
- Many paragraphs end up being quite large (DECISION/CONCLUSION paragraphs especially)

### Case Size Distribution

- **Median paragraphs per case:** 17
- **Average paragraphs per case:** 31
- **P90:** 53 paragraphs per case
- **Max:** 1,727 paragraphs per case

## 3. Proposed Architecture: Three Tools (Tiered Access)

A single `get_case` tool is insufficient because it either returns too much or too little. Instead, a **three-tool family** mirrors the existing design pattern (`get_section` / `get_act_tree` / `search_legislation` already split by granularity in `mcp_server.py`).

### Tool 1: `get_case` — Metadata + Structural Outline (No Paragraph Text)

**Purpose:** Answer "what is this case about?" without touching paragraph content.

**Input parameters:**
- `citation` (string, required) — case citation to look up

**SQL:**
```sql
-- Metadata query
SELECT citation, case_name, court, decision_date::text, judges, outcome,
       related_provisions, related_rulings, head_notes::text
FROM cases WHERE citation = '<escaped_citation>' LIMIT 1;

-- Section outline query (cheap GROUP BY, no content column)
SELECT section_type, COUNT(*) as paragraph_count,
       MIN(sequence_order) as start_seq,
       MAX(sequence_order) as end_seq
FROM case_paragraphs
WHERE case_id = (SELECT id FROM cases WHERE citation = '<escaped_citation>')
GROUP BY section_type
ORDER BY MIN(sequence_order);
```

**Output shape:**
```json
{
  "citation": "[2024] HCA 1",
  "case_name": "Commissioner of Taxation v Example",
  "court": "HCA",
  "decision_date": "2024-02-15",
  "judges": ["Gageler CJ", "Gordon J", "Edelman J"],
  "outcome": "Appeal dismissed",
  "related_provisions": ["ITAA 1997 s 8-1", "ITAA 1997 s 15-15"],
  "head_notes": { ... },
  "paragraph_count": 214,
  "sections": [
    {"section_type": "BACKGROUND", "count": 12, "range": [1, 12]},
    {"section_type": "FACTS", "count": 40, "range": [13, 52]},
    {"section_type": "REASONING", "count": 130, "range": [53, 182]},
    {"section_type": "DECISION", "count": 12, "range": [203, 214]}
  ],
  "cited_by_count": 15,
  "citations_made": 8
}
```

**Guarantee:** No paragraph `content` is fetched. This is always fast (2 cheap queries, no large text columns).

### Tool 2: `get_case_paragraphs` — Paragraph Content on Demand

**Purpose:** Retrieve full text of a subset of paragraphs after the agent sees the outline.

**Input parameters:**
- `citation` (string, required) — identifies the case
- `section_type` (string, optional) — filter to one section type (e.g., `"DECISION"`, `"REASONING"`)
- `range_start` / `range_end` (integers, optional) — `sequence_order` range
- `limit` (integer, optional, default: 50, max: 200) — hard cap on paragraphs returned

**Constraint:** At least one filter must be provided (`section_type` or `range_start`). Calls with no filter and no limit are rejected to prevent accidental full-case dumps.

**SQL:**
```sql
SELECT paragraph_number, paragraph_label, section_type, content, sequence_order
FROM case_paragraphs
WHERE case_id = (SELECT id FROM cases WHERE citation = '<escaped_citation>')
  AND (:section_type IS NULL OR section_type = :section_type)
  AND (:range_start IS NULL OR sequence_order >= :range_start)
  AND (:range_end IS NULL OR sequence_order <= :range_end)
ORDER BY sequence_order
LIMIT :limit;
```

**Output shape:**
```json
{
  "citation": "[2024] HCA 1",
  "filter": {"section_type": "REASONING", "range": [53, 70]},
  "returned_count": 18,
  "total_matching": 130,
  "truncated": false,
  "paragraphs": [
    {
      "paragraph_number": 53,
      "paragraph_label": "53",
      "section_type": "REASONING",
      "content": "The central question in this appeal is whether...",
      "sequence_order": 53
    }
  ]
}
```

### Tool 3: `search_case_paragraphs` — Full-Text Search Within a Case (or Across Cases)

**Purpose:** Let agents find specific paragraphs by content rather than navigating the structure top-down.

**Input parameters:**
- `citation` (string, optional) — scope to one case; if omitted, search all cases
- `query` (string, required) — search terms (uses GIN trigram/tsvector index)
- `section_type` (string, optional) — further filter by section type
- `limit` (integer, optional, default: 20, max: 100)

**SQL (tsquery on content):**
```sql
SELECT cp.paragraph_number, cp.section_type,
       LEFT(cp.content, 300) as snippet,  -- preview only
       cp.sequence_order, c.citation, c.case_name,
       ts_headline('english', cp.content, plainto_tsquery('english', '<query>'),
                   'MaxWords=50, MinWords=20') as headline
FROM case_paragraphs cp
JOIN cases c ON c.id = cp.case_id
WHERE cp.content ILIKE '%<query>%'  -- fallback if tsquery doesn't match
   OR cp.content_fts @@ plainto_tsquery('english', '<query>')
  AND (:citation IS NULL OR c.citation = :citation)
  AND (:section_type IS NULL OR cp.section_type = :section_type)
ORDER BY cp.sequence_order
LIMIT :limit;
```

**Output shape (snippets, not full paragraphs):**
```json
{
  "query": "deductive",
  "citation_filter": "[2024] HCA 1",
  "total_matches": 5,
  "results": [
    {
      "citation": "[2024] HCA 1",
      "case_name": "Commissioner of Taxation v Example",
      "section_type": "REASONING",
      "paragraph_number": 61,
      "snippet": "...the <b>deductive</b> methodology requires...",
      "headline": "...the <b>deductive</b> methodology requires examining the statutory text first..."
    }
  ]
}
```

This tool replaces the need for the old `get_case_sql_data()` approach entirely — an agent can now jump straight to relevant content.

## 4. Implementation Details

### Where to Add Code

**New file:** `backend/services/case_sql_service.py`

Contains three functions mirroring the three tools above:
- `fetch_case_metadata(citation: str) -> dict | None`
- `fetch_case_paragraphs(citation: str, section_type=None, range_start=None, range_end=None, limit=50) -> dict`
- `search_case_paragraphs(query: str, citation=None, section_type=None, limit=20) -> dict`

Reuses `_sql()` and `_sql_dict()` from `tax_case_sql.py` (or import them; may need to refactor to a shared module since they're currently in `tax_case_sql.py`).

**Modification:** `backend/mcp_server.py`

Add three new tool registrations in `list_tools()` and three new handler functions in `call_tool()`.

**Optional:** `backend/routes/tax_cases.py`

Add REST endpoints wrapping the same service functions if API parity is desired.

### SQL Injection Safety

The existing `_sql()` function uses f-string interpolation with manual single-quote escaping (`citation.replace("'", "''")`). For the new service, use one of:
- **Option A (simplest):** Continue with the same escaping pattern + f-strings. Acceptable since: (a) input comes from the MCP tool, not direct user-facing REST, (b) the DB schema has unique constraint on citation, so no blind injection risk for reads.
- **Option B (safer):** Use `psql -v` variables: `psql -v citation="'[2024] HCA 1'" -f query.sql`
- **Option C (recommended for new code):** Use Python's `psycopg2` directly instead of docker exec, if a Python PG driver is acceptable. This gives real parameterized queries.

**Recommendation:** Start with Option A (matching existing pattern) for consistency; add parameterized queries only if a Python PG driver is introduced.

### Connection Strategy

The existing `docker exec cadena-postgres psql ...` pattern works reliably and matches the deployment model. For the three new tools, this is fine — queries are simple aggregate/select operations with LIMITs. No connection pooling needed.

### Pagination for Large Results

`get_case_paragraphs` returns a single page (up to `limit` paragraphs). No cursor-based pagination is needed for now because:
- Most cases are under 53 paragraphs (P90)
- The section_type filter naturally scopes results
- Agents can call multiple times with different ranges

If a case has 1,727 paragraphs and the agent wants to read it all, they can make multiple calls with `range_start`/`range_end` in chunks of 200.

## 5. Relationship to Standalone cadena-knowledge-MCP

The standalone server at `/home/harrison/projects/cadena-knowledge-MCP/` was built for a similar purpose but is:
1. A separate process with its own MCP transport
2. Likely unmaintained / partially broken
3. Duplicative now that the legislation-explorer has direct Postgres access

**Recommendation:** Once these three tools are built and tested, mark the standalone server as **deprecated**. There is no need to port any features from it — the DB schema coverage here (cases + paragraphs + citations + legislation refs) is a superset of what the standalone server likely handled.

## 6. Migration Path

| Step | What | Est. Effort |
|------|------|-------------|
| 1 | Create `backend/services/case_sql_service.py` with `fetch_case_metadata()` | 2-3 hours |
| 2 | Add `get_case` tool registration + handler in `mcp_server.py` | 1 hour |
| 3 | Add `fetch_case_paragraphs()` to the service | 2-3 hours |
| 4 | Add `get_case_paragraphs` tool registration + handler | 1 hour |
| 5 | Add `search_case_paragraphs()` to the service | 2-3 hours |
| 6 | Add `search_case_paragraphs` tool registration + handler | 1 hour |
| 7 | Test all three tools with sample citations (especially edge cases: no paragraphs, huge cases, missing citation) | 2 hours |
| 8 | Document and mark standalone cadena-knowledge-MCP as deprecated | 30 min |
| | **Total** | **~12-14 hours** |

## 7. Open Questions

1. **Should `get_case` also return `case_citations` info (cited by / cites)?** The `case_citations` table exists with paragraph-level context. Could be included in the metadata tool as a summary count + top-5 list. Low-cost since it's a simple aggregate join.

2. **Should `search_case_paragraphs` use ILIKE, tsquery, or both?** Recommendation: try tsquery first (GIN index exists on `content`), fall back to ILIKE. The headline function (`ts_headline`) is valuable for snippet generation.

3. **What about the `head_notes` jsonb field?** Some cases have rich head notes (key holdings, catchwords parsed into structured JSON). `get_case` should return these as-is. If head_notes contain long unstructured text, consider truncating at a sensible limit.

4. **Rate limits / token cost for MCP tool registration?** Adding 3 tools is fine; the MCP list_tools response stays under 16KB easily.

## 8. Appendix: Sample SQL Queries for Reference

### get_case — Section Outline
```sql
SELECT section_type, COUNT(*) as paragraph_count,
       MIN(sequence_order) as start_seq, MAX(sequence_order) as end_seq
FROM case_paragraphs
WHERE case_id = (SELECT id FROM cases WHERE citation = '[2024] HCA 1')
GROUP BY section_type
ORDER BY MIN(sequence_order);
```

### get_case_paragraphs — Filtered
```sql
SELECT paragraph_number, paragraph_label, section_type, content, sequence_order
FROM case_paragraphs
WHERE case_id = (SELECT id FROM cases WHERE citation = '[2024] HCA 1')
  AND section_type = 'REASONING'
  AND sequence_order BETWEEN 53 AND 70
ORDER BY sequence_order
LIMIT 50;
```

### search_case_paragraphs — Full-text within a case
```sql
SELECT cp.paragraph_number, cp.section_type,
       LEFT(cp.content, 300) as snippet,
       cp.sequence_order
FROM case_paragraphs cp
WHERE cp.case_id = (SELECT id FROM cases WHERE citation = '[2024] HCA 1')
  AND cp.content ILIKE '%deductive%'
ORDER BY cp.sequence_order
LIMIT 20;
```

### Citation count (for get_case enrichment)
```sql
SELECT COUNT(*) as cited_by_count
FROM case_citations
WHERE cited_citation = '[2024] HCA 1';
```
