# Phase 2 Plan: Dev Environment, Code Resilience, Database Completion

## 1. Dev Environment — dev.scriptkitty.yachts

**Goal:** A dev/staging instance of the legislation-explorer with no auth, for testing new features before production.

**Current state:** `dev.scriptkitty.yachts` already exists in the Cloudflare tunnel config pointing to `localhost:3000` — which is the Vite frontend dev server. The backend is production-only on `legislation.scriptkitty.yachts`.

**Proposed setup:**

```
dev.scriptkitty.yachts
  ├── Frontend: Vite dev server (already running on :3000) — hot reload, no build step
  └── Backend:  Copy of legislation-explorer service on port 8766
       ├── No Azure AD SSO
       ├── No MCP token auth
       ├── CORS allows dev.scriptkitty.yachts
       └── Points to same data directory (or a copy)
```

**Steps:**
1. Copy the systemd service file → `legislation-explorer-dev.service` on port 8766
2. Create a `.env.dev` with `AZURE_CLIENT_ID=` (empty = no SSO) and `ALLOWED_ORIGINS` including dev subdomain
3. Update Cloudflare tunnel config to route `dev.scriptkitty.yachts` to the backend on 8766 AND the frontend on 3000 (or use a path-based split)
4. Actually simpler: route `dev.scriptkitty.yachts` → `localhost:8766` (backend serves the built frontend too), and the Vite dev server stays on :3000 for local dev only

**Alternative simpler approach:** Just run the existing backend with `--reload` on port 8766 and a dev config:
```bash
cd /home/harrison/legislation-explorer
cp .env .env.dev
# Edit .env.dev: remove AZURE_CLIENT_ID, set ALLOWED_ORIGINS
uvicorn backend.main:app --host 127.0.0.1 --port 8766 --reload
```

**Files to change:**
- `~/.cloudflared/config.yml` — update dev.scriptkitty.yachts → `localhost:8766`
- `legislation-explorer/.env` — add a separate `.env.dev` or use env vars in systemd

---

## 2. Code Simplification for Resilience

**Goal:** Reduce complexity, eliminate failure modes, make the server easier to debug.

### 2a. Remove legacy SSE transport
The MCP server has two transports: SSE (legacy) and StreamableHTTP (new). The SSE code adds complexity with session tracking, token management per session, and raw ASGI middleware. Since StreamableHTTP + OAuth works, kill SSE.

**Files:** `backend/mcp_server.py` — remove `SseServerTransport`, `handle_mcp_sse()`, `_session_tokens`, `mcp_post_message_app()`, `NoopResponse`

### 2b. Consolidate dual auth into single middleware
The OAuth middleware, bearer token middleware, and MCP token auth are three separate code paths. Consolidate into one middleware that checks: (1) JWT from OAuth flow, (2) MCP token query param, (3) fallback bearer token.

**Files:** `backend/main.py` — the dual middleware blocks (lines 75-105) need simplification

### 2c. SQL injection fixes
The `case_db_service.py` uses raw string interpolation (`f"SELECT ... WHERE citation = '{safe}'"`) instead of parameterized queries. Even though `_safe()` escapes single quotes, this is fragile. Switch to parameterized queries.

**Files:** `backend/services/case_db_service.py` — all SQL queries

### 2d. Remove `@lru_cache` on `load_rulings()` and `load_tree()`
These cache data forever, meaning the server needs a restart to pick up new rulings. Replace with a TTL cache or a manual reload endpoint.

**Files:** `backend/services/data_loader.py` — `load_rulings()`, `load_tree()`, `load_definitions()`

### 2e. Simplify `load_rulings()` — deduplicate
The function has two loops (RULING_DIR + ATO_RULING_DIR) with separate URL generation code. Consolidate into one loop with a shared filename parser.

**Files:** `backend/services/data_loader.py` — lines 341-413

### 2f. Standardise error messages
`get_case` has helpful error messages ("Try the bare neutral citation format..."). Other tools just say "not found". Standardise.

**Files:** `backend/mcp_server.py` — all `_get_*` error handlers

---

## 3. Complete the Database

### 3a. TD Ingestion (from BUG_TD_MISSING.md)

**Problem:** Only 40 TD files exist. There should be ~500+ (TDs from 1990s to present).

**Approach:** Use the existing ATO rulings scraping pattern from `cadena-knowledge-MCP/scripts/ingest_ato_rulings.py` with a TD-specific scraper:
1. Scrape ATO TD index pages (TD 1990/1 → TD 2024/...)
2. Download HTML/PDF, extract text, save as `.txt` to `RULING_DIR`
3. Run `load_rulings()` to verify all appear

**Potential locations:**
- ATO website: `/law/view/rulings/td/` — check if TD index exists
- AustLII: `/au/other/rulings/ato/ATOTD/` — has TD files by year

**Files to create:**
- `scripts/ingest_td_rulings.py` — TD-specific scraper (or extend existing `ingest_ato_rulings.py`)

### 3b. Fix Truncated Sections

**Problem:** s 6-1(5) ends mid-sentence (missing "non-assessable non-exempt income) in the hands of a particular entity"). Likely affects other sections too.

**Approach:** Rebuild the markdown files from the Federal Register of Legislation XML source.
1. Locate the original XML source files (likely in cadena-knowledge-MCP pipeline)
2. Re-run the XML → markdown conversion with a fix for subsection boundary detection
3. Compare the old and new markdown files for regressions

**If XML source is gone:**
Use the working FTS5 search index (which has the full text extracted from the original XML) to regenerate the markdown files. The search index stores the full content per section.

**Files to create:**
- `scripts/rebuild_sections.py` — regenerate markdown from search index or XML

### 3c. Full Case Content

**Problem:** `get_case_paragraphs` serves mid-sentence segmented paragraphs. The full case text is stored in the `documents` table (LENGTH up to 147k chars).

**Approach options (choose one):**

**Option A — Direct download:** The `build_download_urls()` already generates AustLII URLs. Add a `GET /api/case-download/{citation}` endpoint that serves the stored document content as a plain text download. Simple, cheap, no chunking needed.

**Option B — Chunked paragraphs:** Re-ingest all cases with proper paragraph boundary detection (split on `[N]` judgment markers, not character windows). This requires re-running the ingestion pipeline with an improved segmenter.

**Option C — Hybrid:** Serve the full document text via `get_case_paragraphs` when `section_types` is omitted (no filter = return all paragraphs as one block). Add a `download_case` parameter to return raw text.

**Recommended:** Option A first (quick win), then Option B when the case re-ingestion pipeline is ready.

**Files to change:**
- `backend/routes/cases.py` — add download endpoint
- `backend/services/case_db_service.py` — add `get_case_document()` function
- `backend/mcp_server.py` — update `download_case` tool to return raw text option

---

## Implementation Order

| Priority | Task | Effort | Dependencies |
|----------|------|--------|-------------|
| 1 | Dev environment setup | 1h | None |
| 2 | TD ingestion | 2-4h | ATO website access |
| 3 | Code simplification (SSE removal, auth consolidation) | 2h | Dev environment for testing |
| 4 | Full case content (Option A) | 1h | None |
| 5 | SQL injection fix | 1h | Code review |
| 6 | TTL cache for load_rulings | 1h | None |
| 7 | Truncated section rebuild | 2-4h | XML source location |
| 8 | Standardise error messages | 30m | None |