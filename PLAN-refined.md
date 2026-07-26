# Cadena MCP ↔ Legislation Explorer — Refined Unification Plan

> Analysis basis: full read of both codebases + **live probing of the production Cadena MCP server** (22 tools invoked). Where the draft assumed DB state, this plan reports what the live DB actually does. DB connection strings in `.env.production` / `.env*` were **not read** (security policy); all counts come from live MCP tool responses, not direct `SELECT`s, so row counts are approximate where noted.

---

## 1. Executive Summary

### The actual data split (verified)

| Data | Cadena MCP (Postgres, tax DB) | Legislation Explorer (files, in-memory) |
|------|-------------------------------|------------------------------------------|
| **Cases** | ~6,959 rows in `cases`; `case_paragraphs` + `case_citations` **exist and work**; summaries are raw AustLII HTML dumps; `outcome`/`provisions` empty | 523 full-text case JSONs (`asic-scraper/cases/`) **+** 3,191 tax-case listing entries (966 HCA + 1,782 FCA + 443 FCAFC) enriched with 2,128 catchwords + 867 section-ref sets |
| **Legislation** | flat `legislation` + `documents`/`chunks`; `provisions` tool returns clean text; **no hierarchy** | hierarchical `tree.json` (Part→Div→Subdiv→Section) for 5 acts + ~11,000 section markdown files |
| **Rulings** | `rulings` metadata + `documents`; `rulings` tool works | 155 `.txt` full-text files — **sourced from `cadena-knowledge-MCP/data/rulings`** (same files) |
| **Commentary** | none — `commentary_links` table does not exist | 3 CCH JSON files — **sourced from `cadena-knowledge-MCP/pipeline/output`** (same files) |
| **Search** | pgvector over `chunks` | SQLite FTS (`search_index.db`) + `embeddings.db` |

### What works / broken / missing (verified live)

**Works:** `index`, `search`, `provisions`, `rulings`, `cases`, `paragraphs`, `top_cases`, `citations`, `search_asic`, `search_aml`, precedents tools. (10+ operational.)

**Broken — exact live errors captured this session:**
| Tool | Live error |
|------|-----------|
| `get_case` | `column c.decision_summary does not exist` |
| `get_case_with_commentary` | `column c.decision_summary does not exist` |
| `get_provision_hierarchy` | `relation "legislative_hierarchy" does not exist` |
| `get_division_sections` | `relation "legislative_hierarchy" does not exist` |
| `get_related_sections` | `relation "section_xrefs" does not exist` |
| `get_commentary` | `relation "commentary_links" does not exist` |
| `suggest_commentary` | `relation "commentary_links" does not exist` |

**Degraded:** `analyze_cases` returns `{"case_name": null}` with no reasoning (resolves identity via the broken summary path). `top_cases` works but ~60% of top rows show `case_name: "(not in database)"` — `case_citations` references citations absent from `cases` (dangling refs). `cases` summaries are AustLII HTML boilerplate, not structured.

### The core insight

**The draft over-estimated the work.** The broken tools are not broken for lack of data engineering — they're broken for two mundane, mechanical reasons:

1. **Three migrations were never run on production:** `001_hierarchical_structure` (`legislative_hierarchy`), `002_commentary_links` (`commentary_links`), `003_section_xrefs` (`section_xrefs`). The tables simply don't exist. (`004_case_structure` — paragraphs/citations — *was* applied; that's why those tools work.)
2. **`004_case_summary_schema` was never run:** the six summary columns (`decision_summary`, etc.) don't exist on `cases`.

**And the data to fill those tables already lives in the Explorer's inputs — which are the MCP repo's own files.** `COMMENTARY_DIR` and `RULING_DIR` in `backend/config.py` point *into* `cadena-knowledge-MCP/`. The Explorer already parses `tree.json` into hierarchy and CCH JSON into `(act, section)` commentary links at load time. So:

- **Easy:** legislative hierarchy, commentary links, and section xrefs can be *derived from files the Explorer already parses* — no new data acquisition, no scraping, no LLM extraction.
- **Hard:** cases. Two different corpora, different keys (citation strings that don't reconcile cleanly), different depth. MCP's catchwords/outcomes are empty; the Explorer's 2,128 catchwords + section-refs are exactly what MCP lacks — but joining them is by fuzzy citation string.

**The draft's Phase 3 (bidirectional sync engine) is over-engineered for the actual problem.** The two systems don't need a live sync; they need MCP's missing tables built + populated once from shared files, and a decision about which system owns cases. Recommend one-way ingestion (files → Postgres), not two-way sync.

---

## 2. Detailed Technical Analysis

### 2.1 MCP subsystem — tool-by-tool status (live-verified)

| # | Tool | Status | Backing table(s) | Notes |
|---|------|--------|------------------|-------|
| 1 | `index` | ✅ operational | taxonomy over `case_legislation_refs`+`documents` | Full topic tree; `case_legislation_refs` exists |
| 2 | `search` | ✅ operational | `chunks`,`documents` | pgvector |
| 3 | `provisions` | ✅ operational | `legislation`,`documents`,`chunks` | Clean section text (verified: ITAA1997 s8-1 returned) |
| 4 | `rulings` | ✅ operational | `rulings`,`documents` | |
| 5 | `cases` | ⚠️ degraded | `cases`,`documents` | Works, but `summary` = AustLII HTML boilerplate, `outcome`/`provisions` null/empty |
| 6 | `top_cases` | ⚠️ degraded | `case_citations`,`cases` | Works; many rows `case_name:"(not in database)"` — dangling citation refs |
| 7 | `paragraphs` | ✅ operational | `case_paragraphs`,`cases` | Works; real `section_type` values observed: `ISSUE`, `BACKGROUND` (not the documented FACTS/REASONING/…) |
| 8 | `citations` | ✅ operational | `case_citations`,`cases` | `case_citations` exists |
| 9 | `analyze_cases` | ❌ broken/empty | depends on summary path | Returned `{"case_name": null}`, no reasoning |
| 10 | `analyze_sections` | ⚠️ partial | `case_legislation_refs`,`case_paragraphs` (+broken summary) | Underlying tables exist but batch analysis leans on broken `get_case` |
| 11 | `get_case` | ❌ broken | `cases` (missing cols) | `column c.decision_summary does not exist` |
| 12 | `get_provision_hierarchy` | ❌ broken | `legislative_hierarchy` | `relation ... does not exist` |
| 13 | `get_division_sections` | ❌ broken | `legislative_hierarchy` | `relation ... does not exist` |
| 14 | `get_related_sections` | ❌ broken | `section_xrefs` | `relation ... does not exist` |
| 15 | `get_commentary` | ❌ broken | `commentary_links` | `relation ... does not exist` |
| 16 | `suggest_commentary` | ❌ broken | `commentary_links` | `relation ... does not exist` |
| 17 | `get_case_with_commentary` | ❌ broken | `cases` (missing cols) + `commentary_links` | `column c.decision_summary does not exist` |
| 18–20 | precedents (`search_precedents`,`get_precedent`,`list_precedents`) | ✅ (separate DB) | `PrecedentsDatabase` | Not in `schema.sql`; own DB |
| 21 | `search_asic` | ✅ (optional DB) | ASIC `chunks`,`documents` | |
| 22 | `search_aml` | ✅ (optional DB) | AML `chunks`,`documents` | |

**Schema-vs-DB reality (corrected from draft):**

| Migration | Tables/cols | Applied to prod? | Evidence |
|-----------|-------------|------------------|----------|
| `001_hierarchical_structure` | `legislative_hierarchy` | **NO** | live `relation ... does not exist` |
| `002_commentary_links` | `commentary_links` | **NO** | live `relation ... does not exist` |
| `003_section_xrefs` | `section_xrefs` | **NO** | live `relation ... does not exist` |
| `004_case_structure` | `case_paragraphs`, `case_citations`, `cases.head_notes` | **YES** | `paragraphs`/`top_cases`/`citations` all return data |
| `004_case_summary_schema` | `cases.decision_summary`, `.reasoning_summary`, `.key_findings`, `.referred_cases`, `.referred_legislation`, `.case_summary`, `.summary_updated_at` | **NO** | live `column c.decision_summary does not exist` |

Also: `schema.sql` is stale (defines only 8 tables); the real schema is `schema.sql` + migrations. Two migrations both prefixed `004` (ordering ambiguity). `005_unified_headnotes_structure.sql` is not valid DDL (contains a Python-dict blob) — treat as a no-op/placeholder. `firm_documents` exists only in pg_dump backups, no tracked DDL, and is not wired to any MCP tool.

**Data counts (from live `index`, topic-tagged so they overlap — not a partition):** income_tax 5,875 · international 2,924 · CGT 1,383 · administration 971 · anti-avoidance 376 (Part IVA 114, Div 7A 26) · trusts 210 (s100A reimbursement 16) · GST 199 · FBT 84 · corporate 81 · super 58. Consistent with a ~6,959-row `cases` table. Exact `COUNT(*)` not obtainable without DB creds.

### 2.2 Explorer subsystem

**Architecture:** FastAPI (`backend/main.py`) + React/Vite. All content loaded from JSON/markdown/text on disk via `@functools.lru_cache`. No relational DB for content (SQLite only for `comments.db`, `search_index.db`, `embeddings.db`).

**Data sources (`backend/config.py`) — 3 of 5 live in sibling projects:**
- `DATA_DIR = ~/legislation-explorer/data` — trees, section markdown, all derived indexes, tax-case listings.
- `CASE_DIR = ~/projects/asic-scraper/cases` — 523 full-text case JSONs `{citation, case_name, year, court, decision_date, source_url, content}`.
- `COMMENTARY_DIR = ~/projects/cadena-knowledge-MCP/pipeline/output` — 3 CCH JSONs (`master_tax_guide.json`, `master_gst_guide.json`, `master_tax_examples.json`).
- `RULING_DIR = ~/projects/cadena-knowledge-MCP/data/rulings` — 155 `.txt` + `.meta.json`.
- `ATO_RULING_DIR = ~/projects/cadena-knowledge-MCP/data/ato_rulings` — **dead path**: dirs hold PDFs, loader globs non-recursively for `*.txt` → 0 results.

**API surface:** `/api/acts`, `/api/tree/{act}`, `/api/section/{act}/{section}`, `/api/cases`, `/api/case/{citation}`, `/api/cases/{act}/{section}`, `/api/rulings-list`, `/api/ruling/{citation}`, `/api/rulings/{act}/{section}`, `/api/ruling-sections/{citation}`, `/api/commentary/{act}/{section}`, `/api/tax-cases[/{court}]`, `/api/section-tax-cases/{act}/{section}`, `/api/smart-links/...`, plus comments/search.

**Primary vs derived:**
- *Primary (on disk):* `{act}/tree.json` + `{act}/sections/**/*.md`; `definitions_all.json`; `CASE_DIR/*.json`; `COMMENTARY_DIR/*.json`; `RULING_DIR/*.txt`; `{court}_tax_cases.json`.
- *Derived build artifacts (in `DATA_DIR`):* `citation_index.json` (6.5MB), `section_case_index.json`, `case_section_refs.json`, `case_catchwords.json`, `ruling_section_index.json`, `smartlink_index.json` (16MB).
- *Derived in-memory at load:* commentary index `{"act:section"→entries}` (`_load_commentary_index`), paragraph index, `short_name`/`category` per case, AustLII URL derivation, section frontmatter parse.

**Frontend consumption:**
- `TaxCaseDetail.tsx`: `title`, `citation`, `hca_url`/`fedcourt_url`/`austlii_url`, `catchwords`, `section_refs[]`. **Does not use full case text** — metadata + external links only.
- `SectionContent.tsx`: `frontmatter{act,part,division,section}`, `body`/`markdown`, `commentary[]{text,page_number}`, `rulings[]{citation,title}`, related tax cases `{citation,court,catchwords}`, comments, smart links.

### 2.3 Overlap analysis

- **Cases — HARD.** MCP ~6,959 cases with paragraph structure but HTML-boilerplate summaries, empty outcomes, dangling citation refs. Explorer: 523 clean full-text JSONs (different source, `asic-scraper`) + 3,191 metadata listings with 2,128 catchwords + section-refs. **No shared key beyond fuzzy citation strings.** The catchwords/section-refs the Explorer computed are exactly what MCP's `cases` rows lack. This is the only genuinely hard merge.
- **Legislation — EASY (derivable).** MCP `legislation` is flat; the *missing* `legislative_hierarchy` wants exactly Part→Division→Subdivision→Section — which is what Explorer `tree.json` already encodes for 5 acts. Derive the MCP hierarchy table directly from `tree.json`. No new data.
- **Rulings — shared source.** Explorer's 155 ruling `.txt` files *are* `cadena-knowledge-MCP/data/rulings`. MCP `rulings` is metadata over the same corpus. Authoritative = the `.txt` files (full text); MCP already serves them via `documents`.
- **Commentary — EASY (shared source, worth ingesting).** MCP has none; the CCH JSON the Explorer reads lives in `cadena-knowledge-MCP/pipeline/output`. Explorer's `_normalize_section_ref` already maps CCH `section_refs` → `(act, section)` — the same normalization populates `commentary_links`. Worth ingesting: 3 files, already parsed, unblocks 2 tools + `get_case_with_commentary`.

---

## 3. Revised Phases

Ordering: fix cheap breakage first (migrations), then derive-and-populate from shared files, then decide on cases. Each phase is independently shippable.

### Phase 0 — Confirm migration state & align schema (0.5 day)
**Why:** the whole diagnosis rests on "001–003 + 004_case_summary not applied." Confirm before touching anything.
- Files: none modified (read-only).
- SQL to run (read-only):
  ```sql
  SELECT to_regclass('public.legislative_hierarchy'),
         to_regclass('public.commentary_links'),
         to_regclass('public.section_xrefs'),
         to_regclass('public.case_paragraphs'),
         to_regclass('public.case_citations');
  SELECT column_name FROM information_schema.columns
   WHERE table_name='cases' ORDER BY 1;
  SELECT count(*) FROM cases;
  SELECT count(*) FROM case_paragraphs;
  SELECT count(DISTINCT section_type) AS n, array_agg(DISTINCT section_type) FROM case_paragraphs;
  ```
- Success: confirms the three tables are NULL, the four summary columns absent, and gives real `cases`/`case_paragraphs` counts + the real `section_type` vocabulary (already known to include `ISSUE`, `BACKGROUND`).

### Phase 1 — Run the unapplied migrations (0.5 day)
**Why:** unblocks 7 broken tools with zero new data (tools return empty-but-valid instead of erroring).
- Apply, in order: `001_hierarchical_structure.sql`, `002_commentary_links.sql`, `003_section_xrefs.sql`, `004_case_summary_schema.sql`. (Full DDL in §4 — use it if repo files are unreliable.)
- Migration hygiene: rename `004_case_summary_schema.sql` → `005_case_summary_schema.sql`; delete/neutralise the invalid `005_unified_headnotes_structure.sql`.
- Success: `get_provision_hierarchy`, `get_division_sections`, `get_related_sections`, `get_commentary`, `suggest_commentary`, `get_case`, `get_case_with_commentary` **no longer error** (they return empty until Phase 2). Re-run the same 7 MCP tool calls from this analysis and confirm no `relation/column does not exist`.

### Phase 2 — Populate from shared files (2–3 days)
One-off ingestion scripts in the MCP repo (`scripts/`). Each reads files the Explorer already parses.

**2a. `legislative_hierarchy` from `tree.json` (0.5 day).** Walk `DATA_DIR/{act}/tree.json` Part→Div→Subdiv→Section, insert a row per node with `parent_id` linkage and `document_id` linked to existing `legislation`/`documents` where the section matches. Acts: itaa-1997, itaa-1936, gst-1999, taa-1953 (nz-it-2007 optional).
- Success: `get_provision_hierarchy('ITAA1997','8-1')` returns Part/Div/Subdiv; `get_division_sections('ITAA1936','Division 7A')` returns the Div 7A section list.

**2b. `commentary_links` from CCH JSON (0.5–1 day).** Port Explorer's `_load_commentary_index` + `_normalize_section_ref` (`data_loader.py`) to emit `(act_code, section, commentary_title, page_number, excerpt)` rows. Embeddings optional (Decision D3) — `suggest_commentary` needs them, `get_commentary` does not.
- Success: `get_commentary('ITAA1936','100A')` returns CCH excerpts with page numbers.

**2c. `case_summary` columns population (1 day) — only if keeping MCP HTML cases.** Backfill `decision_summary`/`reasoning_summary` etc. Cheapest path: derive from existing `case_paragraphs` grouped by `section_type` (no LLM). Structured summaries via LLM → defer to Decision D1.
- Success: `get_case('[2022] HCA 10')` returns a populated (non-null) summary.

**2d. `section_xrefs` (defer — Decision D4).** Requires parsing "see section X" cross-refs from legislation markdown. Lowest value, highest parse effort. Ship the empty table (Phase 1) so the tool stops erroring; populate later only if used.

### Phase 3 — Case reconciliation spike (1 day) — NOT a sync engine
Do **not** build the draft's bidirectional sync. Instead:
- Spike: fuzzy-join Explorer's 2,128 catchwords + section-refs onto MCP `cases` by normalised citation. Measure match rate.
- If match rate high (>85%): one-way backfill — catchwords → `cases` (new `catchwords` column or `case_summary` JSONB), section-refs → `case_legislation_refs`. Fixes empty `provisions`/catchwords and some `top_cases` "(not in database)" dangling refs.
- Success criterion measured, not assumed: report the % of Explorer cases that reconcile to an MCP row.

**Skipped vs draft:** the two `scripts/sync_*.py` and the cron/post-ingest hook. Add a real sync only when the systems actually diverge in production (they currently share files, so they don't).

---

## 4. SQL Migrations (complete DDL)

> Types inferred from the columns the code `SELECT`s (`database.py`, `server.py`). Adjust lengths to match repo migrations if those are authoritative; the point is a runnable schema that satisfies every query in the code.

```sql
-- 001_hierarchical_structure.sql
CREATE TABLE IF NOT EXISTS legislative_hierarchy (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    act_code     VARCHAR(20)  NOT NULL,          -- 'ITAA1997','ITAA1936','GST','TAA1953'
    part         VARCHAR(100),
    division     VARCHAR(100),
    subdivision  VARCHAR(100),
    section      VARCHAR(50),                    -- '8-1','100A'
    title        TEXT,
    document_id  UUID REFERENCES documents(id) ON DELETE SET NULL,
    parent_id    UUID REFERENCES legislative_hierarchy(id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_leghier_act_section  ON legislative_hierarchy(act_code, section);
CREATE INDEX IF NOT EXISTS idx_leghier_act_division ON legislative_hierarchy(act_code, division);
CREATE INDEX IF NOT EXISTS idx_leghier_parent       ON legislative_hierarchy(parent_id);
```

```sql
-- 002_commentary_links.sql   (pgvector already installed for chunks)
CREATE TABLE IF NOT EXISTS commentary_links (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    act_code         VARCHAR(20)  NOT NULL,
    section          VARCHAR(50)  NOT NULL,
    commentary_title TEXT,
    page_number      VARCHAR(50),                -- CCH paragraph numbers e.g. '¶1-010'
    treatment        VARCHAR(50),
    excerpt          TEXT,
    embedding        vector(1536),               -- nullable; only suggest_commentary needs it
    document_id      UUID REFERENCES documents(id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_commlink_act_section ON commentary_links(act_code, section);
CREATE INDEX IF NOT EXISTS idx_commlink_embedding
    ON commentary_links USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

```sql
-- 003_section_xrefs.sql
CREATE TABLE IF NOT EXISTS section_xrefs (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_act     VARCHAR(20) NOT NULL,
    source_section VARCHAR(50) NOT NULL,
    target_act     VARCHAR(20) NOT NULL,
    target_section VARCHAR(50) NOT NULL,
    xref_type      VARCHAR(50),                  -- 'defined_term','exception','modification','penalty'
    context        TEXT,
    created_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_xref_source ON section_xrefs(source_act, source_section);
CREATE INDEX IF NOT EXISTS idx_xref_target ON section_xrefs(target_act, target_section);
```

```sql
-- 005_case_summary_schema.sql   (renamed from the duplicate-004 file)
ALTER TABLE cases
    ADD COLUMN IF NOT EXISTS decision_summary     TEXT,
    ADD COLUMN IF NOT EXISTS reasoning_summary    TEXT,
    ADD COLUMN IF NOT EXISTS key_findings         TEXT[],
    ADD COLUMN IF NOT EXISTS referred_cases       JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS referred_legislation JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS case_summary         JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS summary_updated_at   TIMESTAMPTZ;
```

```sql
-- (Phase 3, optional) catchwords backfill target
ALTER TABLE cases ADD COLUMN IF NOT EXISTS catchwords TEXT;
```

---

## 5. Code Changes

Most fixes are **schema, not code** — once the tables/columns exist, the existing queries work unchanged. The genuine code changes are the ingestion scripts and a couple of query robustness fixes.

**5.1 `scripts/populate_hierarchy.py` (new).** Reads `~/legislation-explorer/data/{act}/tree.json`; inserts `legislative_hierarchy` rows with parent linkage. ~80 lines.

**5.2 `scripts/populate_commentary_links.py` (new).** Port of Explorer `backend/services/data_loader.py::_load_commentary_index` + `_normalize_section_ref`. Reads `~/projects/cadena-knowledge-MCP/pipeline/output/*.json`, inserts `commentary_links`. ~100 lines.

**5.3 `src/cadena_knowledge_mcp/server.py::get_case` (≈L1174).** The broken query selects 6 columns that don't exist yet. After the migration it works as-is. *Optional hardening:* treat null summaries as "fall back to `case_paragraphs` grouped by `section_type`" rather than returning nulls that break `analyze_cases`.

**5.4 `batch_tools.py::analyze_multiple_cases`.** Currently yields `{case_name: null}` when the summary path fails. Change: resolve `case_name` directly from `cases.case_name` (always present) and build reasoning from `case_paragraphs`. Note the real `section_type` vocabulary is **not** the documented `FACTS/REASONING/...`; it includes `ISSUE`, `BACKGROUND`. Make the filter tolerant or normalise on ingest (Decision D2).

**5.5 Explorer — no changes required.** It already reads the shared files. If cases converge to Postgres (Decision D1), a thin `/api/case` shim could query MCP instead of scanning 523 JSONs — opt-in, not required for unification.

---

## 6. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Repo migration files differ from §4 DDL (types/lengths) | Phase 0 dumps `information_schema`; prefer repo files if present, use §4 only to fill gaps. Renaming the duplicate `004` is required either way. |
| Running migrations on prod without backup | A pg_dump (`backup_pre_hierarchy_*.sql`) already exists in the repo — take a fresh one before Phase 1. DDL is `CREATE/ADD ... IF NOT EXISTS`, so re-runnable and non-destructive. |
| `section_type` vocab mismatch silently drops paragraphs in `analyze_cases` | Phase 0 returns the real distinct set; make the reasoning filter tolerant instead of hard-coding `REASONING/ANALYSIS`. |
| Citation strings don't reconcile across corpora (Phase 3) | Treat as a measured spike; ship nothing until match rate is known. Don't backfill on a bad key. |
| Explorer depends on external sibling-project paths | Already true today; document the coupling. Ingesting commentary/rulings into Postgres *reduces* it over time. |
| Embedding cost/time for `commentary_links` | Make `embedding` nullable; ship `get_commentary` (no embedding) first, backfill only if `suggest_commentary` is used. |
| `.env*` not read → connection details unconfirmed | Operator runs migrations with their own creds; this plan never needs the secrets. |

---

## 7. Decision Points (need user input)

- **D1 — Who owns cases?** (a) MCP authoritative, Explorer keeps its 523 full-text JSONs separately; (b) backfill Explorer catchwords/section-refs → MCP, make MCP the single case store; (c) keep both, join by citation on demand. Recommend **(b)** — highest value, uses data that already exists — but only after the Phase 3 spike confirms citation match rate.
- **D2 — Normalise `section_type`?** Real values (`ISSUE`, `BACKGROUND`, …) don't match the documented `FACTS/REASONING/...`. Recommend tolerant consumers over data churn.
- **D3 — Commentary embeddings now or later?** `get_commentary` works without them; `suggest_commentary` needs them. Recommend ship without, backfill only if `suggest_commentary` is used.
- **D4 — Build `section_xrefs` at all?** Lowest value, needs cross-ref parsing. Recommend ship the empty table (stops the error), defer population until the tool has a consumer.
- **D5 — Sync vs one-way ingest?** Recommend dropping the bidirectional sync. Confirm no live-divergence requirement before investing.
- **D6 — ATO rulings PDFs.** The `ato_rulings` path is dead (PDFs, no `.txt`). Ingest those PDFs, or leave the 155 LCG-style `.txt` rulings as the corpus?

---

*Prepared read-only. No code changed, no migrations run. All "broken tool" errors above are live outputs from the production Cadena MCP server captured during this analysis.*
