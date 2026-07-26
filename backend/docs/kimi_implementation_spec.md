# Implementation spec for Kimi Code

You need to add 4 MCP tools to the legislation-explorer backend at /home/harrison/legislation-explorer/.

Read the plan at /home/harrison/legislation-explorer/backend/docs/get_case_PLAN.md for full context.

## Files to create/modify

### 1. NEW: `backend/services/case_db_service.py`

Reuse `_sql()` and `_sql_dict()` from `backend/services/tax_case_sql.py` by importing them (they're currently module-level functions). If import doesn't work, you may need to refactor them into a shared module.

IMPORTANT: tax_case_sql.py uses `docker exec cadena-postgres psql -U postgres -d cadena_knowledge` to run queries. The `_sql_dict(columns, query)` function takes column names and a SQL query string. `_sql(query)` returns raw rows.

Actually, let me check: `_sql_dict` and `_sql` are module-level functions in tax_case_sql.py. You can import them with:
```python
from backend.services.tax_case_sql import _sql_dict, _sql
```

Functions to implement:

#### `get_case_metadata(citation: str, include_legislation_refs: bool = False) -> dict | None`

Two queries:
1. Fetch from `cases` table: citation, case_name, court, decision_date::text, judges, outcome, related_provisions, related_rulings, head_notes::text
   - Also get content_length from `documents` table: SELECT LENGTH(content) FROM documents WHERE id = c.document_id
   - Also get cited_by_count: SELECT COUNT(*) FROM case_citations WHERE cited_citation = '{citation}'
   - Also get legislation_refs_count: SELECT COUNT(*) FROM case_legislation_refs WHERE case_id = c.id

2. Section outline: SELECT section_type, COUNT(*) as count, MIN(sequence_order) as start_seq, MAX(sequence_order) as end_seq FROM case_paragraphs WHERE case_id = (SELECT id FROM cases WHERE citation = '{citation}') GROUP BY section_type ORDER BY MIN(sequence_order)

Also generate download URLs: AustLII URL from citation pattern `https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/{COURT}/{YEAR}/{NUM}.html`. Parse citation like `[2024] HCA 1` → court=HCA, year=2024, num=1.

If include_legislation_refs is True, also fetch: SELECT act_title, section_reference, context, paragraph_number FROM case_legislation_refs WHERE case_id = (SELECT id FROM cases WHERE citation = '{citation}') ORDER BY paragraph_number

Return None if case not found.

#### `get_case_paragraphs(citation: str, section_types: list[str] | None = None, paragraph_start: int = 0, paragraph_limit: int = 50, range_start: int | None = None, range_end: int | None = None) -> dict`

Must enforce: at least one filter (section_types or range_start). If none provided, reject with error.

Enforce: paragraph_limit max 100, and a hard cap of 50,000 chars total content. If 50K is hit before 100 paragraphs, stop.

Also return total_matching count (how many paragraphs match the filter), and total_in_case (how many paragraphs exist in the case).

SQL: SELECT paragraph_number, paragraph_label, section_type, content, sequence_order FROM case_paragraphs WHERE case_id = (SELECT id FROM cases WHERE citation = '{citation}') [AND section_type = ANY(...)] [AND sequence_order >= range_start] [AND sequence_order <= range_end] ORDER BY sequence_order OFFSET paragraph_start LIMIT paragraph_limit

For the FIRST count query (total_matching), run the same query without the LIMIT/OFFSET and use COUNT(*).

Content cap: after fetching results, compute total chars. If > 50,000, truncate the results array and set truncated=true.

#### `search_case_paragraphs(query: str, citation: str | None = None, section_types: list[str] | None = None, limit: int = 10) -> dict`

Uses ILIKE (fractional is fine, no need for tsquery since GIN index may not exist on this table).

If citation is provided (within-case), limit max 100.
If citation is None (cross-case), limit max 30.

Returns: query, citation_filter, total_matches, results array. Each result has: citation, case_name, court, section_type, paragraph_number, snippet (first 300 chars of content), content_length, sequence_order.

SQL pattern:
```sql
SELECT cp.paragraph_number, cp.section_type, LEFT(cp.content, 300) as snippet,
       LENGTH(cp.content) as content_length, cp.sequence_order,
       c.citation, c.case_name, c.court
FROM case_paragraphs cp
JOIN cases c ON c.id = cp.case_id
WHERE cp.content ILIKE '%{query}%'
  AND ({citation} IS NULL OR c.citation = '{citation}')
ORDER BY c.citation, cp.sequence_order
LIMIT {limit}
```

#### `build_download_urls(citation: str) -> dict | None`

Parse citation like `[2025] FCAFC 94`:
- year = 2025, court = FCAFC, num = 94
- AustLII URL: `https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/FCAFC/2025/94.html`

Return dict with austlii_url. Also fetch case_name from DB.

### 2. MODIFY: `backend/mcp_server.py`

Add 4 new tool registrations in `list_tools()`:

**`get_case`** — description: "Get case metadata and structural outline. No paragraph text returned. Use get_case_paragraphs to read paragraphs."
  - Input: citation (required), include_legislation_refs (optional bool, default false)

**`get_case_paragraphs`** — description: "Retrieve paragraphs from a case, filtered by section type and/or sequence range. Use get_case first to see available section types. At least one filter required."
  - Input: citation (required), section_types (optional array of strings), paragraph_start (optional int, default 0), paragraph_limit (optional int, default 50, max 100), range_start (optional int), range_end (optional int)

**`search_case_paragraphs`** — description: "Full-text search across case paragraphs. If citation is omitted, searches ALL cases. Returns snippets."
  - Input: citation (optional string), query (required string), section_types (optional array of strings), limit (optional int, default 10)

**`download_case`** — description: "Get download links for full case text. Use these URLs to download the full case from AustLII or court website for offline research. MCP does not serve full text directly."
  - Input: citation (required)

Add 4 new handler branches in `call_tool()`.

### 3. MODIFY: `backend/routes/tax_case_sql.py`

No changes needed if the functions are properly importable. If _sql_dict or _sql are not importable (e.g. they're inside a class or function), you'll need to refactor them to module-level.

## URL Generation

Citation format is `[YEAR] COURT NUMBER` e.g. `[2024] HCA 1`, `[2025] FCAFC 94`, `[2024] AATA 397`.

Use regex: `\[(\d+)\]\s+(\w+)\s+(\d+)` to extract year, court, number.

AustLII URL pattern: `https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/{COURT}/{YEAR}/{NUM}.html`

## Testing

After writing all code, run a quick test:
1. Restart the backend service (or test via the running dev server)
2. Call each tool with a known citation e.g. `[2024] HCA 1` and check output

Test edge cases:
- Citation not found → returns error gracefully
- No filters on get_case_paragraphs → returns error requiring at least one filter
- search_case_paragraphs without citation → returns cross-case results
- search_case_paragraphs with citation → returns within-case results

## Style

Follow existing code style in mcp_server.py:
- JSON responses via json.dumps(result, indent=2)
- Return [TextContent(type="text", text=...)]
- Error handling with try/except wrapping the handler
- Use single-quote escaping for SQL inputs (citation.replace("'", "''"))
