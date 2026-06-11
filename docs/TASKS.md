# Legislation Explorer v2 — Task Registry

## Legend
- 🔴 Not started
- 🟡 In progress
- 🟢 Completed
- 🟣 Blocked

---

## Feature 1: Auto-Hyperlink Cross-References

| ID | Task | Status | Owner | Notes |
|----|------|--------|-------|-------|
| 1.1 | Expand `LEG_SECTION_RE` to capture subsections: `s 8-1(2)`, `s 6-5(1)(a)` | 🟢 | backend | Done in `main.py` |
| 1.2 | Cross-act reference mapping: `ITAA 1936`, `GST Act`, `FBT Act`, `SIS Act`, `TAA 1953` | 🟢 | backend | `CROSS_ACT_RE` + mapping dict added |
| 1.3 | Link definition terms in non-dictionary section body text | 🟢 | backend | `auto_link_definitions()` added |
| 1.4 | Schedule reference linking: `Schedule 1, item 1` | 🟣 | backend | Blocked on 2.1 (no schedule data in tree yet) |

## Feature 2: More Acts + Fix Schedules

| ID | Task | Status | Owner | Notes |
|----|------|--------|-------|-------|
| 2.1 | Investigate ITAA 1936 schedule files on disk | 🟢 | data | **FINDINGS:** No schedule `.md` files exist in `sections/`. Raw schedule text exists in `raw/vol05.txt` (Schedules 2, 2D, 2F, 2H). Parser `parse_itaa36.py` lacks schedule regex, so schedules were never emitted. Requires parser extension + rebuild to fix. |
| 2.2 | Add FBT Assessment Act 1986 | 🟣 | data | **FINDINGS:** No full structured data. `FBT_Act_KeyProvisions.txt` (summary only, 3.8KB) exists. Full act source missing. Needs source PDF/text + parser. |
| 2.3 | Add SIS Act 1993 | 🟡 | data | **FINDINGS:** `SIS_Act_1993_full.txt` (68k lines, real legislation) exists in `cadena-knowledge-MCP/data/legislation/`. Needs parser script. |
|| 2.4 | Add TAA 1953 | 🟢 | data | **DONE:** Parser written, 1,318 sections created from 4 PDF volumes. tree.json built. Search index rebuilt. Live on site. |

## Feature 2.5: ITAA 1936 Schedules (was Bug B-1)

|| ID | Task | Status | Owner | Notes |
||----|------|--------|-------|-------|
|| 2.5.1 | Parse vol05 (Schedule 2, 2D, 2F, 2H) | 🟢 | data | `parse_itaa36_schedules.py` written and run |
|| 2.5.2 | Emit schedule section markdown files | 🟢 | data | 229 schedule sections + Schedule 2 zone rebate file |
|| 2.5.3 | Update tree.json with schedule nodes | 🟢 | data | 4 schedule nodes added |
|| 2.5.4 | Rebuild search index | 🟢 | data | ITAA 1936 now 1,011 sections (was ~780) |

## Feature 6: Keyboard Shortcuts

| ID | Task | Status | Owner | Notes |
|----|------|--------|-------|-------|
| 6.1 | Add `keydown` listener in `App.tsx` | 🟢 | frontend | Done |
| 6.2 | `j`/`k` next/prev section | 🟢 | frontend | Done |
| 6.3 | `/` focus search | 🟢 | frontend | Done |
| 6.4 | `esc` close drawer / blur search | 🟢 | frontend | Done |
| 6.5 | Shortcut help panel (`?`) | 🟢 | frontend | Modal with key map done |

## Feature 7: Split View / Pin Section

| ID | Task | Status | Owner | Notes |
|----|------|--------|-------|-------|
| 7.1 | Pin state + `localStorage` persistence | 🟢 | frontend | Done |
| 7.2 | Pin button in content header | 🟢 | frontend | Done |
| 7.3 | Pin panel UI (desktop right sidebar) | 🟢 | frontend | Done |
| 7.4 | Mobile pin tabs | 🟢 | frontend | Done |

## Feature 9: Clickable Breadcrumbs

| ID | Task | Status | Owner | Notes |
|----|------|--------|-------|-------|
| 9.1 | Make breadcrumb segments clickable | 🟢 | frontend | Done — scrolls drawer + expands target node |
| 9.2 | Add "Copy citation" button | 🟢 | frontend | Done |

## Feature 10: Search by Section Number

| ID | Task | Status | Owner | Notes |
|----|------|--------|-------|-------|
| 10.1 | Backend: detect section-number query pattern | 🟢 | backend | Done — regex in `/api/search` |
| 10.2 | Backend: exact section lookup by ID | 🟢 | backend | Fast path before FTS5 done |
| 10.3 | Frontend: show "Jump to section" for exact matches | 🟢 | frontend | Top result with distinct styling done |

---

## Bugs

| ID | Description | Status | Blocking |
|----|-------------|--------|----------|
|| B-1 | ITAA 1936 schedules missing from tree | 🟢 | 1.4, 2.1 | **FIXED:** `parse_itaa36_schedules.py` parsed vol05, created 229 schedule sections + Schedule 2 file. tree.json rebuilt with schedule nodes. Search index updated. |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-05-19 | PRD created, task registry initialised |
| 2026-05-19 | Data investigation complete: ITAA 1936 schedules, FBT/SIS/TAA source locations documented |
| 2026-05-19 | Frontend: keyboard shortcuts, pin section, clickable breadcrumbs, search jump all implemented |
| 2026-05-19 | Backend: cross-act refs, auto-link definitions, exact section search all implemented |

---

## Data Investigation Appendix

### ITAA 1936 Schedules (Bug B-1)

**What was checked:**
- `find data/itaa-1936/sections -type f | grep -i sched` → **0 results**
- `grep -i schedule data/itaa-1936/tree.json` → **0 results**
- `grep "^Schedule" data/itaa-1936/raw/vol05.txt` → **7 matches** (Schedule 2, 2D, 2F, 2H)

**Schedules present in raw text:**
- Schedule 2 (Zone rebates / tax tables)
- Schedule 2D — Tax exempt entities that become taxable
- Schedule 2F — Trust losses and other deductions
- Schedule 2H — Demutualisation of mutual entities

**Why they are missing:**
`parse_itaa36.py` only matches:
```python
RE_PART = re.compile(r"^Part\s+([IVX]+)")
RE_DIVISION = re.compile(r"^Division\s+(\d+[A-Z]*)")
RE_SUBDIVISION = re.compile(r"^Subdivision\s+([A-Z]+)")
RE_SECTION = re.compile(r"^(\d+[A-Z]*)\s+(\S.*)$")
```
Schedule headers like `Schedule 2D—Tax exempt entities...` are ignored. Schedule sections use hyphenated IDs (e.g. `57-1`) which do NOT match `RE_SECTION`.

**What is needed to fix:**
1. Add `RE_SCHEDULE = re.compile(r"^Schedule\s+([0-9A-Z]+)")`
2. Extend `ParseContext` with `schedule` / `schedule_title`
3. Update `Section.output_path` to emit `schedule-2d/division-57/57-1.md`
4. Extend `build_tree.py` (or create a post-processor) to add a top-level `schedules` array to `tree.json`
5. Re-run parser on `raw/vol05.txt`

---

### New Acts — Source Data Inventory

| Act | Structured data in `data/`? | Source found? | Location | Size / Quality |
|-----|----------------------------|---------------|----------|----------------|
| **FBT Assessment Act 1986** | ❌ No | Partial | `cadena-knowledge-MCP-oauth-wip/data/legislation/FBT_Act_KeyProvisions.txt` | 3.8 KB summary only. `FBT_Act_1986.docx` is a 404 HTML page. |
| **SIS Act 1993** | ❌ No | ✅ Yes | `cadena-knowledge-MCP/data/legislation/SIS_Act_1993_full.txt` | 68k lines, real legislation scraped from AustLII. |
| **TAA 1953** | ❌ No | ✅ Yes | `cadena-knowledge-MCP-oauth-wip/data/legislation/TAA1953_full.txt` + `TAA1953_vol[1-3].docx` | 34k lines, real legislation. |

**Pipeline scripts available:**
- `pipeline/parse_itaa36.py` — ITAA 1936 (PDF text → markdown)
- `pipeline/parse_itaa97.py` — ITAA 1997
- `pipeline/parse_gst1999.py` — GST Act 1999
- `pipeline/build_tree.py` — Generic tree builder from markdown frontmatter
- `cadena-knowledge-MCP-oauth-wip/data/legislation/scrape_legislation.py` — AustLII scraper (only ITAA 1997 divisions, hard-coded)

**What is needed to add each act:**
1. Obtain full act text (PDF or AustLII HTML)
2. Convert to plain text (`pdftotext -layout` or scrape)
3. Write a parser (modelled on `parse_itaa36.py`) that recognises Part/Division/Section headers
4. Emit markdown with YAML frontmatter
5. Run `build_tree.py` to produce `tree.json`
6. Copy into `legislation-explorer/data/<act-id>/`

**Recommended next step for quickest win:**
TAA 1953 has `TAA1953_full.txt` (plain text, 34k lines). Writing a `parse_taa1953.py` would be the fastest path to a new act, since the source text is already extracted.
