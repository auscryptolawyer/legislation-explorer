# Bug Fix Batch — Legislation Explorer

## Bug 1: get_definition returns wrong anchor for multi-definition terms

**File:** `backend/services/data_loader.py`, function `get_definition_text()` (starts at line 618)

**Problem:** When a term has multiple definitions in the same section (e.g. "dividend" in s 6(1) ITAA 1936), `re.search` finds the first match in body text. The regex `(?<!\w)dividend\s+(?:has\s+(?:the\s+)?(?:same\s+)?meaning|means|includes)` may hit a sub-definition before the primary definition.

**Fix needed:** After finding a match position, check if there's an earlier definition starting line (col-0 anchor line like `dividend includes:`). Prefer the anchor whose immediately preceding text is the bare term itself followed by `includes`, `means`, or `:` at column 0. If multiple anchors match, prefer the primary definition over sub-definitions. Return all matching anchors with a disambiguator when uncertain.

**Test case:**
- Call: `get_definition_text("itaa-1936", "dividend")`
- Should return: the primary definition starting with `dividend includes: (a) any distribution made by a company...`
- NOT: the demerger sub-definition `dividend means that part of a demerger allocation...`

## Bug 2: list_rulings shows placeholder titles for AID/PS LA entries

**File:** `backend/services/data_loader.py`, function `load_rulings()` (starts at line 294)

**Problem:** Title extraction at lines ~348-358 looks for a citation line then takes the next non-empty line. For AID/PS LA entries, the next line after `ATO ID 2004/610` might be "Keywords", "Date of decision:", or other headers instead of the actual title. The `full_title` falls back to `f.stem` which is just the citation.

**Fix needed:** Improve title extraction for AID/PS LA entries. Options:
1. Use the meta file `title` field when available (already done at line 323 for `title` but not for `full_title`)
2. Strip common header keywords from the title extraction result ("Keywords:", "Date of decision:", "Paragraph", "SUBJECT:")
3. Skip lines that are clearly headers (uppercase-only, ends with colon, etc.)
4. Set `full_title` from meta file title when the extracted title looks like a header

**Evidence from bug report:**
```json
{ "citation": "AID_2003_926", "title": "AID_2003_926" }
{ "citation": "AID_2003_936", "title": "Keywords" }
{ "citation": "PSLA_2003_10", "title": "SUBJECT:" }
```

## Bug 3: Cases not on frontend UI

**Problem:** There's no way to browse/search tax cases independently in the web UI. Cases data infrastructure already exists:
- `api.cases()` in `frontend/src/api.ts` 
- `casesData` state in `frontend/src/App.tsx`
- `SectionContent` component already receives `casesData` prop
- Backend has `/api/tax-cases/` endpoints

**Task:** Add a "Tax Cases" option to the act picker dropdown in the sidebar. When selected:
1. Load cases data from `/api/tax-cases` or similar backend endpoint
2. Display cases in the sidebar tree view (court → year → case hierarchy) using the existing TreeNode component
3. When a case is clicked, render its metadata (citation, title, court, date, outcome, catchwords) in the main content area
4. Link to cases on AustLII for full text

**Pattern to follow:** The rulings tree implementation is the closest analogy. Check how `act === 'rulings'` is handled for the sidebar and content area.

**Endpoints available:**
- `GET /api/tax-cases` — list all cases (params: court, year, limit)
- `GET /api/tax-cases/search?q=...` — search cases
- `GET /api/tax-cases/case/{citation}` — individual case metadata

**IMPORTANT:** Do NOT create new React components if possible. Map data into existing types (Tree, Part, Division, Section) and render through existing TreeNode. Follow the "fake tree" / data-mapping pattern: court → Part, year → Division, case → Section.

## Files summary

Files to modify:
- `backend/services/data_loader.py` — Bug 1, Bug 2
- `backend/mcp_server.py` — Bug 1 is MCP handler already fixed? No, the MCP handler calls `get_definition_text()` so fixing that fixes both
- `frontend/src/App.tsx` — Bug 3
- `frontend/src/api.ts` — Bug 3 (if new endpoints needed)
- `frontend/src/components/SectionContent.tsx` — Bug 3 (if cases rendering needs changes)
- `frontend/src/components/TreeNode.tsx` — Bug 3 (check if case IDs need special handling like rulings)

## Testing

After implementing, test:
1. `get_definition_text("itaa-1936", "dividend")` returns the primary definition
2. `load_rulings()` shows proper titles for AID entries
3. Frontend: cases appear in sidebar dropdown and render correctly
4. Existing functionality: legislation sections, rulings, commentary still work
