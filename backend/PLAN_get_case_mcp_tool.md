# Plan: `get_case` MCP Tool Family for Legislation Explorer

## Database Context

| Metric | Value |
|---|---|
| Cases | 7,377 |
| Paragraphs | 226,619 |
| Median paragraphs/case | 17 |
| Mean paragraphs/case | 31 |
| Max paragraphs/case | 1,727 |
| Min doc content length | 1,720 chars |
| Max doc content length | 612,256 chars (~600K) |
| Mean doc content length | ~44K chars |

**Section types** (by paragraph count): DECISION (89K), ISSUE (41K), ORDERS (22K), CONCLUSION (19K), FACTS (17K), HELD (16K), BACKGROUND (4.7K), ANALYSIS (3.8K), REASONING (3K), plus 8.8K untyped.

**Key tables:**
- `cases(id, document_id, citation, case_name, court, decision_date, judges, outcome, related_provisions, related_rulings, head_notes jsonb)`
- `case_paragraphs(id, case_id, paragraph_number, paragraph_label, section_type, content, sequence_order)` — indexed on `(case_id, sequence_order)` and `section_type`
- `documents(id, doc_type, reference, title, content, search_vector)` — full raw text (up to 612K chars)
- `case_legislation_refs(case_id, act_title, section_reference, context, paragraph_number)`
- `case_citations(citing_case_id, cited_citation, cited_case_name, context, paragraph_number)`
- `chunks(document_id, chunk_index, content)` — pre-chunked document pieces

## Existing SQL Access Layer

`tax_case_sql.py` already implements `docker exec` psql queries with:
- `_sql()` / `_sql_dict()` helper functions
- `get_case_sql_data(citation)` — fetches metadata + preview + paragraphs (with 500-char content preview) + chunks
- Type inference for PostgreSQL arrays and jsonb

**Problem:** `get_case_sql_data` already fetches *all* paragraphs with 500-char previews. For the 1,727-paragraph case, that's 863K chars of previews alone. We need smarter tiered access.

## Proposed Design: Family of 4 Tools

Rather than one monolithic `get_case` tool, we expose **4 focused MCP tools** that let the LLM or frontend progressively drill into case details.

### Tool 1: `get_case_metadata` — Case Summary Card

**Purpose:** Return everything *except* full text. Instant, always light.

**Input:**
```json
{
  "citation": "string (required)",
  "format": "string (optional, default 'text' — 'text', 'json', 'markdown')"
}
```

**Returns** (no paragraph content):
- Citation, case_name, court, decision_date
- Judges array, outcome
- related_provisions, related_rulings
- head_notes (parsed JSON → summary text)
- Paragraph count
- Section-type summary (e.g. "BACKGROUND: 12 paras, FACTS: 45 paras, REASONING: 89 paras...")
- Content length (from documents table)
- Hyperlink to AustLII
- Legislation refs count, cited-by count

**SQL:**
```sql
SELECT citation, case_name, court, decision_date::text, judges, outcome,
       related_provisions, related_rulings, head_notes::text,
       (SELECT COUNT(*) FROM case_paragraphs WHERE case_id = c.id) as paragraph_count,
       (SELECT COUNT(*) FROM case_legislation_refs WHERE case_id = c.id) as legislation_refs_count,
       (SELECT COUNT(*) FROM case_citations WHERE citing_case_id = c.id) as cited_by_count,
       (SELECT LENGTH(content) FROM documents WHERE id = c.document_id) as content_length
FROM cases c
WHERE citation = '<sanitized>';
```

Also include a section-type summary using a subquery:
```sql
SELECT section_type, COUNT(*) as count
FROM case_paragraphs WHERE case_id = (SELECT id FROM cases WHERE citation = '<sanitized>')
GROUP BY section_type ORDER BY MIN(sequence_order);
```

**Size estimate:** Always < 2 KB. No content whatsoever.

---

### Tool 2: `get_case_paragraphs` — Structured Paragraph Access

**Purpose:** Retrieve paragraphs by section type, paragraph range, or pagination. This is the main "read the case" tool.

**Input:**
```json
{
  "citation": "string (required)",
  "section_types": ["array of string, optional — filter by section_type, e.g. ['FACTS', 'REASONING']"],
  "paragraph_start": "integer, optional — 0-indexed offset within filtered results",
  "paragraph_limit": "integer, optional — max paragraphs to return (default 20, max 50)",
  "order": "string, optional — 'sequence' (default) or 'paragraph_number'"
}
```

**Returns:**
```json
{
  "citation": "...",
  "case_name": "...",
  "total_paragraphs": 1727,
  "filtered_count": 89,
  "section_types_available": ["BACKGROUND", "FACTS", ...],
  "returned_count": 20,
  "paragraphs": [
    {
      "paragraph_number": 1,
      "paragraph_label": "1",
      "section_type": "BACKGROUND",
      "content": "Full text of paragraph...",
      "sequence_order": 0
    }
  ]
}
```

**Key design decisions:**
- `paragraph_limit` is capped at 50 — the LLM must paginate for more
- Full paragraph content is returned (not truncated) because individual paragraphs are typically short
- `section_types` filter is the primary navigation mechanism: "show me only the REASONING and ANALYSIS sections"
- Pagination uses `paragraph_start` (offset within filtered set), not page numbers — simpler to implement correctly

**SQL pattern:**
```sql
SELECT paragraph_number, paragraph_label, section_type, content, sequence_order
FROM case_paragraphs
WHERE case_id = (SELECT id FROM cases WHERE citation = '<sanitized>')
  AND (section_type = ANY('{FACTS,REASONING}') OR '{FACTS,REASONING}' IS NULL)
ORDER BY sequence_order
OFFSET <paragraph_start> LIMIT <paragraph_limit>;
```

**Size estimate:** Each paragraph averages ~200-500 chars. Max 50 paragraphs × 500 chars ≈ 25 KB. Very manageable.

---

### Tool 3: `search_case_paragraphs` — Full-Text Paragraph Search Within a Case

**Purpose:** Search within the paragraphs of a specific case for a keyword or phrase. Essential for finding "where the judge discussed [topic]" without scrolling.

**Input:**
```json
{
  "citation": "string (required)",
  "query": "string (required)",
  "section_types": ["array of string, optional — restrict search to certain sections"],
  "limit": "integer, optional (default 10, max 30)"
}
```

**Returns:** Matching paragraphs with highlighted context, plus section_type and paragraph_number for navigation.

**SQL:**
```sql
SELECT paragraph_number, paragraph_label, section_type,
       LEFT(content, 300) as content_excerpt,
       LENGTH(content) as content_length,
       sequence_order
FROM case_paragraphs
WHERE case_id = (SELECT id FROM cases WHERE citation = '<sanitized>')
  AND to_tsvector('english', content) @@ plainto_tsquery('english', '<query>')
  AND (section_type = ANY('{...}') OR ...)
ORDER BY sequence_order
LIMIT <limit>;
```

(`ILIKE '%<query>%'` as fallback if PostgreSQL FTS is unavailable or for exact phrase matching.)

**Size estimate:** ≤ 10 KB.

---

### Tool 4: `get_case_legislation_refs` — Related Legislation for a Case

**Purpose:** Show which legislation sections a case references, and optionally in which paragraph.

**Input:**
```json
{
  "citation": "string (required)",
  "act": "string, optional — filter by act"
}
```

**Returns:** List of `{act_title, section_reference, context, paragraph_number}` — typically 5-50 entries.

**Also for citation graph (could be a parameter or separate tool):**

`get_case_citations` returning `{cited_citation, cited_case_name, context, paragraph_number}` — who this case cites.

---

## What About the Full Text?

**Never via MCP.** The `documents.content` column can be up to 612K chars. Three alternatives:

1. **Chunks table already exists** — `chunks(document_id, chunk_index, content)`. Expose chunk retrieval as part of `get_case_paragraphs` or a dedicated tool if needed.
2. **Document download via REST** — Add a REST endpoint `/api/cases/{citation}/download` that returns the full text as a file (triggering browser download). Not an MCP tool.
3. **Use paragraph-level access as default** — 99% of use cases are "show me the FACTS and REASONING" which Tool 2 covers.

## Implementation Plan

### Phase 1: Backend Service

Create `/home/harrison/legislation-explorer/backend/services/case_db_service.py`:

```python
"""PostgreSQL-backed case access service for the MCP get_case tool family."""

from typing import Any
from backend.services.tax_case_sql import _sql_dict as sql

CASE_BY_CITATION_COLS = [
    "id", "citation", "case_name", "court",
    "decision_date", "judges", "outcome",
    "related_provisions", "related_rulings", "head_notes"
]

def get_case_metadata(citation: str) -> dict[str, Any] | None:
    # Primary query joining cases + documents for length
    # + paragraph count + section_type summary subquery
    ...

def get_case_paragraphs(
    citation: str,
    section_types: list[str] | None = None,
    offset: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    ...

def search_case_paragraphs(
    citation: str,
    query: str,
    section_types: list[str] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    ...

def get_case_legislation_refs(
    citation: str,
    act: str | None = None,
) -> list[dict[str, Any]]:
    ...

def get_case_citations(
    citation: str,
) -> list[dict[str, Any]]:
    # Returns cases that cite this case AND cases this case cites
    ...
```

### Phase 2: MCP Tool Registration

In `mcp_server.py`, add to `list_tools()`:
```python
Tool(
    name="get_case_metadata",
    description="Get case summary/metadata without paragraph content. Includes headnotes, section-type breakdown, and paragraph counts.",
    inputSchema={
        "type": "object",
        "properties": {
            "citation": {"type": "string", "description": "Case citation (e.g. [2020] HCA 42)"},
        },
        "required": ["citation"],
    },
),
Tool(
    name="get_case_paragraphs",
    description="Retrieve paragraphs from a case, filtered by section type and with pagination. Use get_case_metadata first to see available section types. Max 50 paragraphs per call — paginate with paragraph_start for more.",
    inputSchema={
        "type": "object",
        "properties": {
            "citation": {"type": "string"},
            "section_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional filter by section type: BACKGROUND, FACTS, ISSUE, ANALYSIS, REASONING, HELD, DECISION, CONCLUSION, ORDERS",
            },
            "paragraph_start": {"type": "integer", "default": 0},
            "paragraph_limit": {"type": "integer", "default": 20, "maximum": 50},
        },
        "required": ["citation"],
    },
),
Tool(
    name="search_case_paragraphs",
    description="Full-text search within the paragraphs of a specific case. Returns matching paragraph excerpts with section types.",
    inputSchema={
        "type": "object",
        "properties": {
            "citation": {"type": "string"},
            "query": {"type": "string", "description": "Search term or phrase"},
            "section_types": {"type": "array", "items": {"type": "string"}},
            "limit": {"type": "integer", "default": 10, "maximum": 30},
        },
        "required": ["citation", "query"],
    },
),
```

### Phase 3: Tool Implementations

In `call_tool()`, dispatch to new handlers, e.g.:
```python
elif name == "get_case_metadata":
    from backend.services.case_db_service import get_case_metadata
    result = get_case_metadata(arguments["citation"])
    if result is None:
        return [TextContent(type="text", text=json.dumps({"error": "Case not found"}))]
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
```

### Phase 4: Testing

- Test with a short case (1-2 paragraphs) — confirm metadata + paragraph retrieval works
- Test with a long case (e.g. 1,727 paragraphs) — confirm section-type filtering and pagination work
- Test search within case paragraphs
- Test case-not-found scenario
- Test docker exec failure (degraded gracefully returns error)

## Workflow for an LLM Using These Tools

The intended usage pattern:

1. `search_cases("FCT v. Smith")` → get a list of matching cases with citations
2. `get_case_metadata("[2023] FCA 123")` → see headnotes, section-type breakdown (e.g. "FACTS: 45 paras, REASONING: 89 paras")
3. `get_case_paragraphs("[2023] FCA 123", section_types=["FACTS"])` → read the facts
4. `get_case_paragraphs("[2023] FCA 123", section_types=["REASONING"])` → read the reasoning
5. `search_case_paragraphs("[2023] FCA 123", query="capital gains")` → find specific discussion topics
6. `get_case_legislation_refs("[2023] FCA 123")` → see which sections of the ITAA were cited
7. If more depth needed: paginate with `paragraph_start=20` to read the next batch

## Why This Design?

- **Never dumps full text** — The `documents.content` column (up to 612K chars) is never queried by MCP tools
- **Section_type is the primary navigation axis** — Legal reasoning has a natural structure (FACTS → ISSUE → ANALYSIS → REASONING → HELD → DECISION → CONCLUSION → ORDERS). We leverage this instead of arbitrary page numbers
- **Small, predictable response sizes** — Every tool call returns < 25 KB except unusual edge cases
- **Composable** — LLMs can mix and match tools: metadata to orient, paragraphs to read, search to find
- **Replaces the broken standalone MCP** — The cadena-knowledge-MCP server can be deprecated once this ships
