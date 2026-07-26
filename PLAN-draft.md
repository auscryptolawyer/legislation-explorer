# Cadena MCP ↔ Legislation Explorer Unification Plan (Draft)

## Goal
Both systems serve from identical underlying data. A case viewed in the legislation explorer shows the same paragraphs as the MCP's `get_case`. A section in the explorer shows the same cases the MCP's `find_cases_on_section` returns. No manual sync. No divergent copies.

---

## Current Data Split

| Data | MCP (Postgres) | Explorer (JSON/files) |
|------|---------------|----------------------|
| Cases | 6,959 rows. `cases`, `case_paragraphs`, `case_citations`, `case_legislation_refs` tables | `case_catchwords.json`, `section_case_index.json`, court JSONs |
| Legislation | 7,312 provisions in `documents` table (flat, no hierarchy) | Full tree (`tree.json`) + markdown sections per act |
| Rulings | `rulings` table (metadata only) | `.txt` files in `data/rulings/`, `data/ato_rulings/` |
| Commentary | None | CCH Master Tax Guide / GST Guide / Examples in `pipeline/output/` |
| Definitions | None | `definitions_all.json` |
| Search | pgvector semantic search on `chunks` | SQLite FTS (`search_index.db`) |

**Problem:** Two copies of overlapping data. Case catchwords live in explorer JSON but not in MCP case records. Legislation hierarchy lives in explorer trees but not in MCP. Ruling full text lives in explorer files but not in MCP documents.

---

## Phase 1: Populate MCP with Explorer Data

### 1.1 Create `legislative_hierarchy` table
Derive from `data/*/tree.json` files (ITAA 1997, ITAA 1936, GST 1999, TAA 1953). Map Part → Division → Subdivision → Section with document_id links.

### 1.2 Add `catchwords` to `cases` table
Populate from `data/case_catchwords.json` + court JSON files. Also populate `related_provisions` array from existing `case_legislation_refs`.

### 1.3 Ingest legislation markdown into `documents`
Read `data/*/sections/*.md`, chunk, embed. Link to `legislative_hierarchy` rows.

### 1.4 Ingest CCH commentary into `documents`
Read `pipeline/output/*.json`, chunk by paragraph, embed. Link to legislation sections via section refs.

### 1.5 Create `section_xrefs` table
Parse cross-references from legislation markdown ("see also section 25-5", "subject to section 8-1").

### 1.6 Create `system_info` tool
Report tool health, DB counts, last sync timestamp.

---

## Phase 2: Fix MCP Tools

| Tool | Current State | Fix |
|------|--------------|-----|
| `get_case` | Queries missing `decision_summary` column | Read `case_paragraphs` grouped by `section_type` |
| `get_case_with_commentary` | Same as above | Same fix + join commentary |
| `analyze_cases` | `case_name: null` | Pull `case_name` from `cases` table directly |
| `get_provision_hierarchy` | Missing `legislative_hierarchy` table | Read from new table |
| `get_division_sections` | Missing table | Read from new table |
| `get_related_sections` | Missing `section_xrefs` table | Read from new table |
| `get_commentary` | Missing `commentary_links` table | Query `documents` where doc_type='guidance' |
| `suggest_commentary` | Missing table | Semantic search over commentary documents |

---

## Phase 3: Sync Layer (Not Refactor)

Keep explorer backend as-is. Add lightweight sync scripts:

- `scripts/sync_mcp_to_explorer.py`: New cases/paragraphs from MCP → explorer JSON indices
- `scripts/sync_explorer_to_mcp.py`: New legislation, rulings, commentary from explorer pipelines → Postgres

Run on cron or post-ingestion hook. No API changes to explorer.

---

## Open Questions

1. **Case text duplication:** MCP stores full case text in `case_paragraphs`. Explorer stores court JSONs with catchwords. Should explorer case detail fetch from MCP via API, or should we sync paragraph text into explorer JSON?
2. **Ruling storage:** MCP `rulings` table has metadata only. Should ruling full text live in `documents` + `chunks` for semantic search, or stay as flat files?
3. **Commentary embeddings:** CCH commentary is structured (chapter → heading → paragraph). Should we preserve hierarchy in Postgres or flatten to chunks?
4. **Definitions:** Static reference data. Keep as JSON or ingest to DB?
5. **Search:** Two search indices (pgvector + SQLite FTS). Converge to pgvector only, or keep both?
