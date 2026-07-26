# Legislation Explorer — Embedding Phase Complete

## What Was Built

### 1. Embedding Pipeline (`scripts/embed_legislation.py`)
- BGE-small-en-v1.5 (384-dim, 33M params, MIT license)
- Chunking at 1,800-char boundaries with sentence-aware splitting
- Dictionary sections (995-1, 6, 195-1) chunked per-definition
- Incremental: hash-based skip for unchanged files
- Cross-reference extraction from definitions, cases, commentary, smartlinks

### 2. Embedding Database (`data/embeddings.db`)
- **22,016 total chunks** across all data
- **83,936 cross-references** (defined terms, cases, commentary links, smartlinks)
- **95 MB** on disk

| Source | Act | Chunks | Sections |
|--------|-----|--------|----------|
| section | itaa-1997 | 6,452 | 4,638 |
| section | nz-it-2007 | 4,891 | 3,262 |
| commentary | master-tax-guide | 4,867 | 1,393 |
| section | itaa-1936 | 1,896 | 1,000 |
| section | taa-1953 | 1,692 | 1,288 |
| commentary | master-gst-guide | 1,232 | 425 |
| section | gst-1999 | 986 | 827 |

### 3. Vector Search API
- `GET /api/search/hybrid?q=...` — hybrid RRF search (FTS5 + vector)
- `backend/services/vector_search_service.py` — in-memory matrix, 5ms query time
- Pre-warms on server startup (BGE model + embedding matrix)
- Cross-references included in response per result

### Dependencies
- `sentence-transformers` (added to backend/venv)
- `BAAI/bge-small-en-v1.5` (cached, ~130MB)

### Next Steps (Phases 2-4)
- **Eval:** Create golden query→section pairs to measure enrichment impact
- **Defined terms:** Extract actual definition text from dictionary sections (not just anchors)
- **Cross-ref injection:** Only if eval proves it helps
- **NZ IT 2007 commentary:** None exists yet