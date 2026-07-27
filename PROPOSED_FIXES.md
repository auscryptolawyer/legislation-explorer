# Proposed Fixes — Legislation Explorer MCP (Batch 2)

Based on the full tool test report. Priority-ordered.

---

## P1: get_definition — remove 500-char cap + boundary detection

**Files:** `backend/services/data_loader.py`

### Changes to `get_definition_text()`:

1. Remove the arbitrary 500-char truncation (lines 716-717)
2. Find actual definition boundary by scanning for the next definition anchor in the markdown body (`<a id="...">` or `#### term` patterns), or the next col-0 heading/footnote
3. Add response fields:
   - `truncated: bool` — whether the returned text is a window (not full definition)
   - `full_text_available: bool` — whether the complete definition is in the section content
4. Fall back to returning the full section text if boundary detection fails, with `truncated: false`

**Key regex change:** The current `m2 = re.search(r'\n(?=[^\s>#<\-\[\('\\'"])', rest)` at line 698 is too broad — it fires on any vertical whitespace followed by a non-special char. Replace with:
```python
# Terminate at the next definition anchor or heading
m2 = re.search(r'(?:\n)(?=\w)', rest)  # col-0 word start
m3 = re.search(r'\n####\s', rest)  # next definition heading
m4 = re.search(r'\n<a id="', rest)  # next anchor
```

And for the `enterprise` / `gst-1999` bleed case, the definition for "enterprise" is a cross-reference (`has the meaning given by section 9-20`) — the code should only return text up to the first sentence boundary (`.`) if the definition is a single-sentence cross-reference.

---

## P2: withdrawn/status — all three ruling tools

**Files:** `backend/services/data_loader.py`

### In `load_rulings()`:

1. Expand `withdrawn` detection beyond the first 1000 chars (line 369). Scan the full content for:
   ```python
   withdrawn_patterns = [
       r'\bis withdrawn\b',
       r'\bhas been withdrawn\b',
       r'\bis now withdrawn\b',
       r'\bArchived\b',
       r'This ATO ID is withdrawn',
       r'\bhas been replaced by\b',
       r'\bsuperseded\b',
       r'\bno longer current\b',
   ]
   withdrawn = any(re.search(p, content, re.IGNORECASE) for p in withdrawn_patterns)
   ```

2. Add `status` field: `"current"` | `"withdrawn"` | `"superseded"` | `"under_review"` based on content scanning

3. Add `withdrawn_reason` (truncated to 300 chars) and `superseded_by` fields

### In `_list_rulings()` in `mcp_server.py`:

- Ensure `withdrawn` field is included in the output (currently only `get_rulings_for_section` includes it)
- `get_ruling()` should also return the `withdrawn` and `status` fields

---

## P3: get_case_paragraphs — re-segmentation

**Files:** `backend/services/case_db_service.py`
**Difficulty:** High — DB-level change; ingestion pipeline fix not feasible here.

### Short-term fix (this batch):

1. Add `judgment_paragraph_number` field alongside the existing `paragraph_number` — extracted from the first `[N]` or `N.` pattern at the start of each paragraph's content
2. In the handler, detect if paragraph numbering looks synthetic (consecutive integers starting from 1 with no `[N]` pattern in content) and flag it
3. Add `warning: str | None` field to the response if paragraphs may be poorly segmented:
   ```python
   "warning": "Paragraphs may be segmented mid-sentence. Cross-reference with the full judgment before citing."
   ```

### Medium-term fix (not this batch):
- Re-ingest all cases with court-specific paragraph markers (AustLII `<hr>` tags, judgment `[N]` markers)
- Re-run the ingestion pipeline with a paragraph-aware segmenter

---

## P4: Paginate/filter list_rulings + get_act_tree

**Files:** `backend/mcp_server.py`

### `list_rulings` — add filter params:

```python
inputSchema={
    "type": "object",
    "properties": {
        "type": {"type": "string", "description": "Filter by ruling type (TR, TD, PCG, AID, PS LA, LCG, etc.)"},
        "year": {"type": "integer", "description": "Filter by year"},
        "limit": {"type": "integer", "description": "Max results (default 100, use 0 for all)", "default": 100},
        "offset": {"type": "integer", "description": "Pagination offset", "default": 0},
        "counts_only": {"type": "boolean", "description": "Return only the year→type histogram (fast)", "default": false},
    },
}
```

When `counts_only=True`, return just the histogram (what the test report calls for). When type/year/limit are set, filter and paginate.

### `get_act_tree` — add depth param:

```python
inputSchema={
    "type": "object",
    "properties": {
        "act": {"type": "string", "description": "Act ID"},
        "depth": {
            "type": "string",
            "enum": ["parts", "divisions", "sections"],
            "description": "Detail level: 'parts' returns only parts list, 'divisions' includes divisions, 'sections' includes all sections (default)",
            "default": "sections"
        },
    },
    "required": ["act"],
}
```

When `depth="parts"`, strip all children (sections/divisions) — just return the parts array with id+title. This reduces MASSIVE payloads to ~31 items for ITAA 1997.

---

## P5: AID titles

**Status:** Already fixed in commit `e77c8714` and `a679f94f`. Verified working in code. The test report's "not fixed" verdict was against the production server which doesn't have these commits yet. Deploy the branch.

---

## P6: get_case — decision_date + empty metadata

**Files:** `backend/services/case_db_service.py`

### decision_date fix:
The issue is the DB stores `2016-01-01` (year-only default). The fix should:
1. Try to extract the real date from the document content if available
2. OR check if the date is Jan 1 (year-only placeholder) and add a `date_note: "Year only — exact date unknown"` field
3. Add `decision_date_source: "document_body" | "database" | "estimated"` field

### Empty judges, outcome, head_notes:
These are null in the DB because the ingestion pipeline never populated them. For this batch:
1. Parse the full document content to extract judges from headnote patterns
2. Parse outcome from final paragraphs
3. Blacklist AustLII navigation strings from `key_terms`

Since the document content is in the `documents` table (LENGTH = 147330 chars for Bywater), we can extract this content and regex it.

```python
# Extract judges from document content if DB is empty
if not judges:
    doc_rows = _sql_dict(["content"], f"SELECT content FROM documents WHERE id = (SELECT document_id FROM cases WHERE citation = '{safe}')")
    if doc_rows and doc_rows[0].get("content"):
        content = doc_rows[0]["content"]
        # Hunt for judge names: "French CJ, Kiefel, Bell, Gageler, Keane, Nettle, Gordon JJ"
        jm = re.search(r'(?:French CJ|Kiefel|Bell|Gageler|Keane|Nettle|Gordon|Edelman|Steward|Gleeson|McHugh|Gummow|Kirby|Hayne|Heydon|Crennan|Kitto|Taylor|Menzies|Windeyer|Owen|Barwick|McTiernan|Fullagar|Dixon|Williams|Webb|Rich|Starke|Evatt|Latham|Higgins|Isaacs|Barton|O\'Connor|Griffith)[\w\s,]*JJ', content)
        if jm:
            judges = [j.strip() for j in jm.group().split(",")]
```

---

## P7: get_section truncation audit

**Files:** `backend/services/data_loader.py` (the `get_act_section_content()` function)

The issue is that s 6-1(5) is truncated mid-sentence. This is a content-extraction problem, likely in the ingestion pipeline (converting Federal Register XML → markdown). The fix for this batch:

1. Add `truncated` detection: compare the section content length against a known expected value, or check if the last line ends with a sentence fragment
2. Add `complete: bool` flag to the response: `true` if the body appears complete, `false` if truncated
3. Add `source_length: int` and `body_length: int` fields for transparency

The actual truncation fix requires fixing the markdown generation pipeline — out of scope for this batch.

---

## P8: Hygiene fixes

### Strip ATO web chrome from ruling content

**File:** `backend/services/data_loader.py` in `load_rulings()`:

Add a cleaning pass in the URL generation section (after line 499):

```python
# Strip ATO web chrome from preview
for r in rulings:
    chrome_patterns = [
        r'^Legal database / Contents / Download / Email / Print / Back to browse\s*\n',
        r'Legal Database\s*\n',
    ]
    for pat in chrome_patterns:
        r["preview"] = re.sub(pat, "", r["preview"], flags=re.IGNORECASE | re.MULTILINE)
```

Also strip chrome from the `content` field in `_get_ruling()` in `mcp_server.py`.

### Remove source filesystem paths

**File:** `backend/services/data_loader.py` line 376: Change `"source": str(f)` to an opaque ID:

```python
"source": f.stem,  # just the filename, no path
```

### court_url passthrough in download_case

**File:** `backend/services/case_db_service.py` `build_download_urls()`:

Add court-specific URLs:
```python
result["court_url"] = None
if parsed:
    court = parsed["court"]
    if court == "HCA":
        result["court_url"] = f"https://www.hcourt.gov.au/cases/case_{year}_{num}.html"
    elif court in ("FCA", "FCAFC"):
        result["court_url"] = f"https://www.judgments.fedcourt.gov.au/judgment/Judgments/{court}/{year}/"
```

### content_length in download_case

Change the hardcoded `"content_length": None` to actually query the DB (similar to `get_case_metadata` does).

---

## P9: Snippet centring + section-number ranking

### search_case_paragraphs — centre snippet on match

**File:** `backend/services/case_db_service.py` `search_case_paragraphs()`:

Replace the current `LEFT(cp.content, 300)` snippet with a centred window:

```python
def _snippet(content: str, query: str, window: int = 150) -> str:
    idx = content.lower().find(query.lower())
    if idx == -1:
        return content[:300]
    start = max(0, idx - window)
    end = min(len(content), idx + len(query) + window)
    snippet = content[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(content):
        snippet = snippet + "..."
    return snippet
```

Also add `<mark>` highlighting around the query term in the snippet.

### search_legislation — section-number ranking

**File:** `backend/services/search_service.py` `search_sections()`:

Add a match-sorting step: if the query looks like a section number (`\d+-\d+`, `\d+[A-Z]`), exact-match against section IDs first:

```python
def search_sections(query, act=None, limit=20):
    results = _fts_search(query, act, limit)
    
    # Check if query looks like a section number
    section_re = re.match(r'^(\d+[A-Z]?-\d+[A-Za-z]*(?:\(\d+\))?)$', query.strip())
    if section_re:
        section_id = section_re.group(1)
        # Exact-match it as rank 0
        for i, r in enumerate(results):
            if r.get("section", "").lower() == section_id.lower():
                results.insert(0, results.pop(i))
                break
        # Truncate to limit
        results = results[:limit]
    
    return results
```
