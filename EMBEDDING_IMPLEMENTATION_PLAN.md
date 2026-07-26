# Embedding Implementation Plan — Legislation Explorer

## Overview

Add vector embeddings to legislation-explorer, leveraging existing infrastructure (FTS5 search, definitions index, citation index, commentary index, smartlink index, markdown processors) to create a semantic search that understands defined terms, cross-references, and commentary relations per section.

## Data Inventory (reviewed — 13,199 files, 145MB)

| Source | Files | Status |
|--------|-------|--------|
| GST Act 1999 (827 sections) | YAML + markdown | ✅ Complete |
| ITAA 1936 (~1,000 sections) | YAML + markdown | ✅ Complete |
| ITAA 1997 (4,638 sections) | YAML + markdown | ✅ Complete |
| TAA 1953 (1,288 sections) | YAML + markdown | ✅ Complete (72 unclassified) |
| NZ IT 2007 (3,295 sections) | YAML + markdown | ✅ Complete |
| Master GST Guide (425 paras) | YAML + markdown | ✅ Complete |
| Master Tax Guide (1,393 paras) | YAML + markdown | ✅ Complete |
| Master Tax Examples (333) | YAML + markdown | ✅ Complete |
| ATO Rulings | 0 | ❌ Empty |

## Existing Infrastructure (to reuse)

| Component | What it does | How we use it |
|-----------|-------------|---------------|
| `load_definitions(act)` | Returns 1,858 defined terms with anchors | Enrich embedding text with definition text per section |
| `get_commentary_for_section(act, section)` | Returns commentary paragraphs discussing a section | Enrich section embedding with commentary context |
| `get_cases_for_section(act, section)` | Returns cases citing a section | Enrich section embedding with case citations |
| `get_smartlinks_for_item("section", "act#section")` | Returns cross-referenced sections | Build cross-reference graph |
| `_load_paragraph_index()` | Maps ¶ numbers to section IDs | Build commentary→legislation relation table |
| `link_definitions()` / `auto_link_definitions()` | Extracts `*term*` references from body | Source for which terms each section uses |
| `link_legislation_refs()` | Extracts section references from body | Source for inline cross-references |
| `link_cch_paragraph_refs()` | Extracts ¶ references from body | Source for commentary→legislation links |
| `get_act_section_content(act, section)` | Reads section frontmatter + body | Core embedding text source |
| Existing FTS5 search (12,937 indexed) | BM25 keyword search | Hybrid ranking partner for vector search |

## Architecture

### Model: BGE-small-en-v1.5
- 33M params, 384-dim vectors, MIT license
- Runs on CPU at ~100ms/doc = ~22 min for 13K docs
- Total index: ~20MB vectors + ~15MB metadata

### Storage: SQLite with numpy BLOBs (no sqlite-vec dependency)
- **Alternative A**: `sqlite-vec` extension (needs .so compilation)
- **Alternative B** (preferred): Store float32 arrays as BLOBs, compute cosine similarity in Python
  - No external dependency, works on any platform
  - 13K × 384-dim scan = ~50ms in numpy
  - Simpler to deploy

### Embedding Schema

```sql
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY,
    act TEXT,
    section TEXT,
    section_title TEXT,
    part TEXT,
    division TEXT,
    corpus TEXT,          -- 'legislation' | 'commentary' | 'ruling'
    embedding BLOB,       -- float32 384-dim array as bytes
    embedding_text TEXT,  -- the text that was embedded (for debugging)
    body_excerpt TEXT,    -- first 500 chars for display
    UNIQUE(act, section)
);

CREATE TABLE cross_references (
    id INTEGER PRIMARY KEY,
    source_act TEXT,
    source_section TEXT,
    target_act TEXT,
    target_section TEXT,
    ref_type TEXT,        -- 'section', 'case', 'commentary', 'definition', 'ruling'
    target_title TEXT,
    snippet TEXT
);
CREATE INDEX idx_cross_ref_source ON cross_references(source_act, source_section);
CREATE INDEX idx_cross_ref_target ON cross_references(target_act, target_section);
```

## Implementation Plan

### Phase 1: Core Embedding Pipeline (~2h)

**Step 1:** Install `sentence-transformers` + download BGE model (~500MB)

**Step 2:** Write `scripts/embed_legislation.py` that:
- Walks the existing tree.json for each act to get all sections (same traversal as `init_search_index`)
- For each section: reads frontmatter + body via `get_act_section_content()`
- Builds embedding text: `[Title]: {title}\n[Act]: {act}\n[Section]: {section}\n{body}`
- Computes 384-dim vector
- Writes to `data/embeddings.db`

**Step 3:** Also embed commentary files (read from `data/master-*-guide/sections/*.md`)

**Output:** `data/embeddings.db` with 13,199 rows, ~20MB

---

### Phase 2: Defined Terms Enrichment (~1h)

**Reuses:** `load_definitions(act)`, `auto_link_definitions()` logic

For each section:
1. Load its body text
2. Use `auto_link_definitions()` to find which defined terms the section uses
3. Look up each term's definition text from `load_definitions(act)`
4. Append to embedding text:
   ```
   [Defined terms]:
   trading stock: trading stock has the meaning given by section 70-5
   cost: cost has the meaning given by subsection 70-20(1)
   ```
5. Recompute embeddings for sections that have defined terms

**Benefit:** "what is trading stock" matches s 70-1 even if the section body doesn't use that phrase.

---

### Phase 3: Cross-Reference Graph (~1.5h)

**Reuses:** `get_cases_for_section()`, `get_smartlinks_for_item()`, `get_commentary_for_section()`, `link_legislation_refs()`

For each section:
1. **Cases**: `get_cases_for_section(act, section)` → case citations
2. **Smartlinks**: `get_smartlinks_for_item("section", f"{act}#{section}")` → cross-referenced sections
3. **Commentary**: `get_commentary_for_section(act, section)` → guide paragraphs
4. **Inline refs**: Parse body with `link_legislation_refs()` patterns → section references
5. **Inline ¶ refs**: Parse body with `link_cch_paragraph_refs()` patterns → paragraph references

Store in `cross_references` table. Also enrich embedding text:
```
[References]: s 70-5, s 195-1, [2012] FCA 414
[Commentary]: Master Tax Guide ¶10-040, Master GST Guide ¶15-090
```

---

### Phase 4: Commentary Embedding with Context (~1h)

**Reuses:** `get_commentary_for_section()`, `_load_paragraph_index()`

For each commentary file:
1. Parse frontmatter for act, section, paragraph number
2. Use `get_commentary_for_section(act, section)` to find which legislation sections it discusses
3. Build embedding text:
   ```
   [Title]: 75% "reduced" input tax credit ¶10-040
   [Guide]: Australian Master GST Guide
   [Content]: As financial supplies are input taxed...
   [Discusses]: GST Act s 70-5, s 70-5.02
   ```
4. Embed and store in same `embeddings` table (corpus='commentary')

**Benefit:** "reduced input tax credit" returns both the commentary ¶10-040 AND the legislation s 70-5.

---

### Phase 5: Search API (~1h)

**Reuses:** Existing `/api/search` route, FTS5 search service

Add to `backend/routes/search.py`:

```python
@router.get("/api/vector-search")
def vector_search(q: str, act: str | None = None, corpus: str | None = None, limit: int = 10):
    # 1. Embed query with BGE model
    # 2. Cosine similarity scan against stored embeddings
    # 3. Join with cross_references for related items
    # 4. Return ranked results
```

**Hybrid search** (combine with existing `/api/search`):
- Vector search → semantic matches (70% weight)
- FTS5 BM25 → keyword matches (30% weight)
- Normalize scores, blend, return merged results

**Response format:**
```json
{
  "results": [
    {
      "act": "ITAA 1997",
      "section": "70-1",
      "title": "What this Division is about",
      "score": 0.89,
      "snippet": "...deals with amounts you can deduct...",
      "defined_terms": ["trading stock", "cost", "market value"],
      "cross_references": [
        {"type": "section", "target": "70-5", "act": "ITAA 1997", "title": "Meaning of trading stock"},
        {"type": "commentary", "target": "¶10-040", "guide": "Master GST Guide", "title": "75% reduced ITC"}
      ]
    }
  ]
}
```

---

## Implementation Order (~6.5h total)

| Phase | What | Time | Key Reuse |
|-------|------|------|-----------|
| 1 | Core embedding (body text only) | 2h | `get_act_section_content()`, tree.json traversal |
| 2 | Defined terms enrichment | 1h | `load_definitions()`, `auto_link_definitions()` |
| 3 | Cross-reference graph | 1.5h | `get_cases_for_section()`, `get_smartlinks_for_item()`, `get_commentary_for_section()` |
| 4 | Commentary embedding | 1h | `get_commentary_for_section()`, `_load_paragraph_index()` |
| 5 | Search API + hybrid ranking | 1h | Existing `/api/search`, FTS5 |

## Open Questions

1. **sqlite-vec vs numpy BLOBs** — numpy BLOBs are simpler to deploy (no compiled extension). Columns: prefer numpy unless scan time becomes an issue.
2. **Model warm-up** — BGE model takes ~2s to load on first request. Options: pre-warm on startup, or lazy-load.
3. **NZ IT 2007** — no NZ commentary. Cross-references to Australian acts may exist but are likely minimal.
4. **ATO Rulings** — `data/rulings/` is empty. Can be added later via Cadena MCP.
5. **Embedding refresh** — when legislation is updated, embeddings need recomputation. Can be triggered by compilation_no change.