# Legislation Explorer — Semantic Search Plan

## Overview
Add vector embedding search to legislation-explorer, linking all legislation and commentary semantically. Small, self-contained, no external dependencies.

## Data Inventory

### Primary Legislation (11,048 sections)
| Act | Sections | Coverage |
|-----|----------|----------|
| GST Act 1999 | 827 | Complete, part/division/section structure |
| ITAA 1936 | 1,000 | Complete, part/division structure |
| ITAA 1997 | 4,638 | Complete, part/division/section structure |
| TAA 1953 | 1,288 | Complete, some parts unclassified |
| NZ IT 2007 | 3,295 | Complete, all parts (A-Z) |

### Commentary (2,151 items)
| Guide | Items | Content |
|-------|-------|---------|
| Master GST Guide | 425 | Paragraph-level commentary with legislative references (e.g., s 63-10) |
| Master Tax Guide | 1,393 | Paragraph-level commentary with legislative references |
| Master Tax Examples | 333 | Worked examples keyed to legislation sections |

**Total: 13,199 files, 145MB**

## Architecture

### Embedding model: BGE-small-en-v1.5
- 33M params, 384-dim vectors
- MIT licensed, runs on CPU at ~100ms/doc
- Best quality/size ratio for legal text
- Alternative: BGE-base-en-v1.5 (102M params, 768-dim) for better quality at ~2x compute cost

### Storage: SQLite with sqlite-vec extension
- No separate vector DB needed
- Single file, easy backup
- sqlite-vec is the simplest vector extension for SQLite
- Query: `SELECT * FROM embeddings ORDER BY vector_distance(embedding, ?) LIMIT 10`

### Embedding pipeline (one-time, ~5 min total)
1. Walk all `data/**/*.md` files
2. Extract: frontmatter (act, part, section, title), body text, file path
3. Concatenate: `title + body` as embedding text
4. Compute 384-dim vector with BGE model
5. Store in `data/embeddings.db` with metadata (path, act, section, title, embedding)

### Search API (FastAPI route on existing server)
```
GET /api/search?q=who pays gst on mixed supplies&limit=5
```
1. Embed query with same BGE model
2. Cosine similarity against 13K stored vectors (~50ms scan)
3. Return results with: title, act, section, excerpt, relevance score

### Architecture integration with existing codebase
- legislation-explorer already serves content at `legislation.scriptkitty.yachts:8765`
- Add `/api/search` route to existing FastAPI app
- Embedding model loads on first request, stays in memory (~100MB)
- sqlite-vec loaded as extension on app start

## Data Quality Improvements

### 1. Cross-reference commentary to legislation
Commentary paragraphs reference sections (e.g., "s 63-10"). Embedding them alongside legislation means:
- "Who can register for GST" returns GST Act Div 23 AND Master Guide ¶10-100 in one search
- Query "ceasing to be a sub-entity" returns s 63-10 AND the guide's ¶15-090 explaining it

### 2. Fix unclassified divisions
TAA 1953 has 72+ sections under `part-unknown/division-unknown` — these have correct content but wrong paths. The embeddings would still work (vector search doesn't care about directory structure), but fixing the paths would enable:
- Proper act/part/division filtering in search results
- Better cross-referencing with commentary

### 3. Multi-layer indexing (legislation only vs legislation+commentary)
Store a `corpus` field: `legislation` or `commentary`. Users can filter:
- `?q=...&corpus=legislation` — statute only
- `?q=...&corpus=commentary` — guides only
- Default: both

### 4. Hybrid search (vector + keyword)
Vector search is great for semantics, bad for precise section lookups. Layer on:
- Full-text search (SQLite FTS5) for exact phrase matching
- Weighted blend: 70% vector + 30% keyword
- Cross-reference boost: commentary paragraphs that reference matching sections get a relevance bump

### 5. Cadena content (future)
No Cadena content is in legislation-explorer currently. The cadena-content-pipeline (Webflow CMS, 11 modules) runs separately. To add it:
- Export Webflow CMS content as markdown
- Add to `data/cadena/` with frontmatter (topic, practice area)
- Run embedding pipeline — it joins the same vector index

### 6. ATO rulings
The `data/rulings/` directory exists but is empty (0 files). Adding ATO rulings (via Cadena MCP or scraping) would be valuable — they directly connect legislation sections to practical interpretations.

## Implementation Order

### Phase 1: Core Search (ready after voice training finishes)
1. Install `sentence-transformers` (pip install, ~500MB download for BGE model)
2. Write `scripts/embed_legislation.py` — walks files, computes embeddings, writes sqlite-vec DB
3. Add `/api/search` route to existing FastAPI app
4. Verify: search queries return relevant results from both legislation and commentary

Estimated: 2-3 hours of dev time, runs in under 5 min on CPU

### Phase 2: Hybrid Search
1. Add FTS5 full-text search table alongside vectors
2. Implement weighted blend (vector 70%, keyword 30%)
3. Add cross-reference boost for commentary→legislation links
4. Add corpus filter (legislation vs commentary)

Estimated: 2 hours

### Phase 3: Data Enrichment
1. Fix TAA 1953 unclassified paths
2. Add Cadena Webflow content
3. Populate rulings (ATO Rulings via Cadena MCP)
4. Add cross-reference linking table (which commentary paragraphs reference which legislation sections)

Estimated: 3-4 hours (depends on content source access)

## Technical Details

### Embedding text format for optimal search
```
[Title]: Mixed supply rules
[Act]: GST Act 1999
[Section]: s 9-5
[Content]: You are liable for GST on any taxable supply you make...

[Title]: Mixed supplies ¶12-010
[Guide]: Australian Master GST Guide
[Content]: A supply that is partly creditable and partly non-creditable...
```
This format means a search for "mixed supply GST" will match both the legislation section and the commentary paragraph, and return them ranked by relevance.

### Index size estimate
- 13,199 docs × 384-dim × float32 = ~20MB for vectors
- Metadata + FTS index = ~15MB
- Total: ~35MB — tiny, even for the Raspberry Pi

## Dependencies
- `sentence-transformers` — for BGE model loading and inference
- `sqlite-vec` — SQLite vector extension (loadable module, no pip needed)
- `sqlite-utils` — optional, for easy DB management

## Constraints
- Must run on the existing legislation-explorer server (Raspberry Pi / low-end VPS)
- No GPU required — BGE-small runs on CPU, 100ms/doc = ~20 min total for 13K docs
- No API keys or external services
- Must integrate with existing FastAPI app, not replace it