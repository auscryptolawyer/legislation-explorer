# RAG + Cross-Reference System — Implementation Plan

## Current State

| Data | Count | Embedded? | Cross-refs? |
|---|---|---|---|
| Legislation sections | 8,661 (8 acts) | ✅ 22,016 vectors (BGE-small 384d) | ✅ section_case_index.json (381 sections → cases) |
| AI-generated summaries | 11,339 documents | ❌ | ❌ (in metadata but not indexed) |
| Ruling texts | 5,999 (non-AID) | ❌ | ❌ |
| ATO ID texts | 5,931 | ❌ | ❌ |
| Tax cases | 7,375+ in PostgreSQL | ❌ | ✅ case_section_refs.json (867 cases → sections) |
| Cross-references DB | 83,936 rows (embeddings.db) | — | ✅ Legislation ↔ legislation |
| Smartlink index | 16MB JSON | — | ✅ Section → section links |

**Key insight**: The core cross-reference data already exists (`section_case_index.json`, `case_section_refs.json`). The missing pieces are semantic embeddings for rulings/cases/commentary and a unified relevance scoring system.

---

## Phase 1 — Unified Embedding Pipeline

### 1a. Expand embeddings.db to cover all content

**Content to embed:**

| Source | Items | Chunks | Est. vectors |
|---|---|---|---|
| Legislation sections (existing) | 8,661 | 22,016 | 22,016 |
| Ruling summaries (AI-generated) | 11,339 | 11,339 | 11,339 |
| Ruling raw texts (non-summarized) | ~490 | ~500 | ~500 |
| Case summaries (from DB) | 7,375 | 7,375 | 7,375 |
| Commentary sections | ~2,500 | ~2,500 | ~2,500 |

**Total**: ~43,730 vectors

**Approach**: Use the existing BGE-small model (already loaded by `vector_search_service.py`). Run a batch embedding script that:

1. Reads from PostgreSQL (cases, rulings with summaries via `metadata->>'ai_summary'`)
2. Reads from data files (legislation sections, commentary)
3. Chunks large content (>512 tokens) with overlap
4. Embeds with BGE-small (384d)
5. Inserts into `embeddings.db` with type field (`section`, `ruling`, `case`, `commentary`)
6. Rebuilds cross-reference table with section↔case links

### 1b. Rebuild FTS5 search index

**Fix `search_index.db`** (0 bytes):
- Run `scripts/rebuild_search_index.py` — builds FTS5 for legislation sections + rulings
- Add FTS5 for case names/citations and commentary sections
- This gives instant keyword search, vector search gives semantic similarity

---

## Phase 2 — Cross-Reference Scoring System

### 2a. Reference frequency database

New table: `reference_graph` in PostgreSQL or separate SQLite:

```sql
CREATE TABLE reference_graph (
    source_type TEXT,       -- 'section', 'case', 'ruling', 'commentary'
    source_id TEXT,         -- 'itaa-1997:8-1', '[2025] HCA 30', 'TR 2024/1'
    target_type TEXT,
    target_id TEXT,
    frequency INTEGER DEFAULT 1,       -- how many times source references target
    semantic_score REAL DEFAULT 0,      -- cosine similarity (0-1)
    combined_score REAL GENERATED ALWAYS AS (frequency * 0.3 + semantic_score * 0.7)
);
CREATE INDEX idx_ref_src ON reference_graph(source_type, source_id);
CREATE INDEX idx_ref_tgt ON reference_graph(target_type, target_id);
```

### 2b. Reference extraction pipeline

| Direction | Data source | Method |
|---|---|---|
| Section → Cases | `section_case_index.json` (already exists) | Parse frequency from list length |
| Case → Sections | `case_section_refs.json` (already exists) | Direct mapping |
| Ruling → Sections | Text regex: `ITAA 1997 s 8-1` | `re.findall(act_section_pattern, text)` |
| Ruling → Cases | Text regex: `[2025] HCA 30` | `re.findall(citation_pattern, text)` |
| Commentary → Sections | Manual curation + text regex | Similar to rulings |
| All → All (semantic) | Vector similarity | BGE-small cosine > 0.75 threshold |

### 2c. Combined relevance score

```
relevance = (citation_frequency_normalized * 0.3) + (semantic_similarity * 0.7)
```

For each content item, pre-compute top-20 related items across all types. Store in `related_items` table.

---

## Phase 3 — API Endpoints

### 3a. Related content endpoint

```
GET /api/related/{type}/{id}?limit=20&types=section,case,ruling,commentary
```

Returns:
```json
{
  "source": {"type": "section", "act": "itaa-1997", "section": "8-1"},
  "related": {
    "cases": [
      {"citation": "[2024] FCA 123", "title": "...", "relevance": 0.92, "refs": 5}
    ],
    "rulings": [
      {"citation": "TR 2024/1", "title": "...", "relevance": 0.85, "refs": 3}
    ],
    "commentary": [
      {"publication": "Master Tax Guide", "section": "6.1", "relevance": 0.78}
    ],
    "sections": [
      {"act": "itaa-1997", "section": "8-2", "relevance": 0.71, "title": "..."}
    ]
  }
}
```

### 3b. Graph data endpoint

```
GET /api/graph/{type}/{id}?depth=1&max_nodes=50
```

Returns node-edge structure for D3/vis.js:
```json
{
  "nodes": [
    {"id": "itaa-1997:8-1", "type": "section", "label": "s 8-1", "group": "itaa-1997"},
    {"id": "[2024] FCA 123", "type": "case", "label": "FCA 123", "group": "fca"},
    {"id": "TR 2024/1", "type": "ruling", "label": "TR 2024/1", "group": "ruling"}
  ],
  "edges": [
    {"source": "itaa-1997:8-1", "target": "[2024] FCA 123", "weight": 0.92, "type": "semantic"},
    {"source": "itaa-1997:8-1", "target": "TR 2024/1", "weight": 0.85, "type": "reference"}
  ]
}
```

### 3c. Hybrid search (upgrade existing)

```
POST /api/search/hybrid
{
  "q": "capital gains main residence",
  "types": ["section", "case", "ruling", "commentary"],
  "limit": 30
}
```

Returns results from all content types ranked by RRF fusion (FTS5 BM25 + vector cosine), with cross-reference enrichments.

---

## Phase 4 — UI Integration

### 4a. Related panel (below content view)

On every section/case/ruling page, a collapsible "Related" panel showing:

```
▾ Related (23 items)
  ├─ Cases (8)          s 8-1 cited in 8 cases
  │  ├─ [2024] FCA 123   ━━━━━━━━━━━━━ 0.92  5 refs
  │  ├─ [2025] HCA 30    ━━━━━━━━━━━  0.85   3 refs
  │  └─ ...
  ├─ Rulings (5)
  │  ├─ TR 2024/1        ━━━━━━━━━━   0.88
  │  └─ ...
  ├─ Commentary (7)
  └─ Sections (3)
```

Each item is clickable → navigates to that content. Relevance bar width = score.

### 4b. Graph explorer page

New route: `/graph?type=section&id=itaa-1997:8-1`

Interactive graph using a lightweight library (D3 force layout or vis-network):

- **Nodes**: colored by type (green=section, blue=case, orange=ruling, purple=commentary)
- **Edges**: thickness = relevance score, color = relationship type
- **Interactions**: click node → expand, drag, zoom, hover for detail
- **Controls**: depth slider (1-3), type filter toggles, search box

---

## Phase 5 — Data Freshness

### 5a. Incremental update pipeline

Built into the monthly cron (`monthly_update.py`):

1. After scanning for new/updated content
2. Only re-embed changed items (use content hash comparison)
3. Update `reference_graph` for new references
4. Recompute top-20 related items for affected nodes
5. No full rebuild needed — incremental only

### 5b. Embedding cost estimate

With BGE-small (free, local model):
- ~43,730 items × 384 dimensions
- ~1.5 hours to embed all (in-memory batch processing)
- ~67MB total vector storage
- ~400MB RAM for model at runtime (already loaded)

---

## Implementation Order

| Step | What | Effort | Why first |
|---|---|---|---|
| 1 | Fix FTS5 index (rebuild search_index.db) | 30 min | Gets search working now |
| 2 | Batch embed all content (script) | 2h | Foundation for everything |
| 3 | Build reference_graph from existing indexes | 1h | Data enrichment |
| 4 | Related content API endpoint | 2h | Unlocks UI work |
| 5 | Related panel in UI | 3h | User-visible improvement |
| 6 | Hybrid search upgrade | 1h | Better ranking |
| 7 | Graph data endpoint | 1h | Backend for graph |
| 8 | Graph explorer UI | 4h | Visual exploration |
| 9 | Incremental update integration | 1h | Production readiness |

**Total**: ~15 hours
