# v2.8 — Implementation Plan

## Overview

Extend Legislation Explorer from tax-only to multi-domain (corps, AML, ASIC, insolvency). Same architecture (PDF → markdown → tree → FTS5 → embeddings), replicated per domain with namespace-prefixed tools.

---

## 1. Pipeline: Corporations Act 2001

### Source
- PDF from ComLaw / Federal Register of Legislation
- Split into raw text via `pdftotext -layout` (same as ITAA 1997)
- Multiple volume PDFs (probably 7-10 volumes)

### Files needed
| File | Purpose | Pattern |
|---|---|---|
| `pipeline/parse_corps_2001.py` | Parse raw text → markdown sections | Same as `parse_itaa97.py` |
| `pipeline/build_tree_corps_2001.py` | Build tree.json from sections | Same as `build_tree.py` |

### Known format differences from ITAA 1997
- Sections are numbered sequentially (1, 2, 3...) not hyphenated (6-5)
- Chapters use roman numerals or single digits (Ch 1, Ch 2A, Ch 7)
- Parts within chapters: Part 1.1, Part 1.2... or Part 1, 1A, 2A etc.
- Need regex patterns for: `Section 1`, `Chapter 1`, `Part 1.1`, `Division 1`, `Subdivision A`

### Data layout
```
data/corps-2001/
├── raw/
│   ├── vol01.txt
│   └── ...
├── sections/
│   └── part-1-1/
│       └── division-1/
│           └── 1.md
├── tree.json
└── definitions.json
```

### Estimated effort: medium
- ~3,000 sections, similar structural complexity to ITAA 1997
- Regex patterns need adaptation but same architecture

---

## 2. Pipeline: AML/CTF Act 2006

### Source
- Single PDF from Federal Register of Legislation
- Smaller act than Corps (~300 sections, ~6-8 chapters/structure levels similar to GST act)

### Files needed
| File | Purpose |
|---|---|
| `pipeline/parse_aml_ctf_2006.py` | Parse raw text → markdown sections |

### Known format
- Chapters 1-4
- Parts numbered 1.1, 2.1 etc.
- Sections sequentially numbered through the act (not per-chapter)
- Division 1A, Division 2 etc.
- ~170 pages, much smaller than Corps

### Data layout
```
data/aml-ctf-2006/
├── raw/
│   └── aml-ctf.txt
├── sections/
└── tree.json
```

### Estimated effort: low
- Small act, simple structure
- Can reuse GST act parser pattern directly

---

## 3. Pipeline: ASIC Rulings

### Source
- ASIC website / AustLII for regulatory guides, class orders, legislative instruments
- Unclear format: HTML pages, PDFs, or structured data

### Options (need confirmation on source format)

**Option A — Scrape (if HTML):**
- `pipeline/scrape_asic_rulings.py` — like `scrape_ato_ids.py` pattern
- Paginated listing → individual pages → extract content
- Store as `.txt` files with metadata JSON alongside

**Option B — PDF batch (if published as downloadable bulletins):**
- `pipeline/parse_asic_rulings.py` — download → pdftotext → extract
- Mixed with structured metadata (date, status, topic tags)

### Data layout
```
data/asic-rulings/
├── raw/
│   ├── RG_1.txt
│   ├── RG_1.meta.json
│   ├── CO_09_1.txt
│   ├── RG_100.txt
│   └── ...
└── tree.json (grouped by category/year)
```

### Tool
- `asic_get_ruling(citation)` — same pattern as `get_ruling`
- Citation format: `RG 1`, `CO 09/1`, `LR` (legislative instrument)

### Estimated effort: medium-high (depends on source format)
- Need to discover the actual source format first
- AustLII has ASIC rulings but may not have full text
- ASIC website may require scraping with bot protection

### Pending confirmation
- Source URL or data dump
- Format (HTML, PDF, structured)
- How many documents (~1,000 is estimate, could be 500-2,000)

---

## 4. Pipeline: Keays Insolvency Textbook

### Source
- User will upload the source file next message
- Likely a PDF of "The Law of Insolvency in Australia" by Keays
- ~20-30 chapters

### Approach
- Textbook is **not** legislation — no section numbers, no case cross-references from embeddings
- Best suited to **full-text search** rather than section lookup
- Pipeline: PDF → pdftotext → chapter-split → FTS5 index

### Architecture option
```
data/insolvency-keays/
├── raw/
│   └── keays.txt (or per-chapter files)
├── chapters/
│   ├── 01-introduction.md
│   ├── 02-voluntary-administration.md
│   └── ...
└── ch-tree.json (map of chapter numbers → titles)
```

### Tool design
```
insolvency_search(query, limit=20)
  → Full-text search across all chapters
  → Returns chapter + excerpt

insolvency_get_chapter(chapter_number)
  → Returns full chapter text
```

### Estimates
- ~300-400 pages total
- ~20-30 chapters
- Low structural complexity (no sections/divisions hierarchy)
- No embeddings similarity needed (unless we want chapter-to-chapter similarity)

---

## 5. Tool Namespace Refactor

### Current
```python
@mcp.tool()
async def get_section(act, section): ...         # tax only
async def get_ruling(citation): ...               # tax only
async def search_all(query, type_filter, act): ...  # tax only
```

### Target
```python
@mcp.tool()
async def tax_get_section(act, section): ...       # existing, renamed
async def tax_get_ruling(citation): ...             # existing, renamed
async def tax_search_all(query, type_filter, act): ...  # existing, renamed

@mcp.tool()
async def corps_get_section(section): ...           # new
async def aml_get_section(section): ...             # new
async def asic_get_ruling(citation): ...            # new

@mcp.tool()
async def insolvency_search(query, limit): ...      # new
async def insolvency_get_chapter(chapter): ...      # new

@mcp.tool()
async def search_all(query, type_filter, domain): ... # cross-domain
```

### Migration
- Keep old `get_section` as an alias during transition
- Mark old names as deprecated, remove in v2.9
- OR keep both (pollution) — decision needed

### Alternative considered: parameterised
```python
get_section(domain="corps", section="1")  # vs corps_get_section("1")
```
- Rejected: tool discovery is worse (LLM has to know the domain parameter exists)
- LLMs pick the right tool by name — `corps_get_section` is immediately discoverable

---

## 6. Cross-Domain `search_all`

### Current FTS5 schema
- `sections_fts(act, section, title, content)` — tax only
- `rulings_fts(citation, title, content)` — ATO rulings only
- `sections_meta(act, section, title, part, division)` — tax only

### Updated schema
- Add `domain` column to `sections_fts` (values: `tax`, `corps`, `aml`, `insolvency`)
- Add `corps_sections_fts` / `aml_sections_fts` / `keays_chapters_fts` — separate tables
- OR keep all in one table with domain discriminator

**Recommendation:** One `sections_fts` table with `domain` column. Simpler for `search_all` queries.  
Add `search_sections` function to accept `domain: str | None = None`.

### search_all expansion
```python
async def search_all(
    query: str,
    type_filter: str | None = None,    # section, case, ruling, commentary, chapter
    domain: str | None = None,          # tax, corps, aml, insolvency, asic
    limit: int = 20,
) -> str:
```
- New `domain` parameter lets LLM narrow search to one domain
- Adds `chapter` type for insolvency textbook

---

## 7. Embeddings Similarity Index

### Current
- `embeddings.db` has tax sections only
- `similarity_index` computes section→case and section→ruling cross-type edges

### Expansion
- Add corps/AML sections to embeddings DB
- Corps sections have no case/ruling references (different legal domain)
- Embeddings useful for: similar-corps-section lookup, not cross-type
- Consider separate `corps_embeddings.db` to keep tax/corps similarity isolated

### Decision needed
- Cross-domain similarity (tax section close to AML section?) — probably not useful
- Better to keep per-domain similarity indices

---

## 8. Implementation Order

### Phase 1 (corps + AML — parallel)
1. Create `data/corps-2001/raw/` and `data/aml-ctf-2006/raw/`
2. Write `parse_corps_2001.py` and `parse_aml_ctf_2006.py`
3. Run parsers, verify output quality
4. Build tree.json for each
5. Regenerate search index

### Phase 2 (tool refactor)
6. Rename existing tools → `tax_*` prefix
7. Add `corps_get_section`, `aml_get_section`
8. Add backward-compatible aliases

### Phase 3 (ASIC rulings — depends on format discovery)
9. Discover ASIC source format
10. Write scraper/parser
11. Add `asic_get_ruling`

### Phase 4 (Keays textbook)
12. Receive file → analyze format
13. Write parser
14. Add `insolvency_search` and `insolvency_get_chapter`

### Phase 5 (cross-domain search)
15. Rebuild FTS5 index with `domain` column
16. Update `search_all` with domain filter

---

## 9. Checklist

- [ ] Corps Act — PDF → raw text
- [ ] Corps Act — parser (`parse_corps_2001.py`)
- [ ] Corps Act — tree.json
- [ ] Corps Act — `corps_get_section` tool
- [ ] AML/CTF Act — PDF → raw text
- [ ] AML/CTF Act — parser (`parse_aml_ctf_2006.py`)
- [ ] AML/CTF Act — tree.json
- [ ] AML/CTF Act — `aml_get_section` tool
- [ ] ASIC rulings — format discovery
- [ ] ASIC rulings — scraper/parser
- [ ] ASIC rulings — `asic_get_ruling` tool
- [ ] Keays textbook — source analysis
- [ ] Keays textbook — parser
- [ ] Keays textbook — `insolvency_search` / `insolvency_get_chapter`
- [ ] Tool namespace refactor (`tax_*` prefix)
- [ ] `search_all` cross-domain update
- [ ] FTS5 index rebuild with domain column
