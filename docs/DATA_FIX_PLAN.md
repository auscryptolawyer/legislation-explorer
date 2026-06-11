# Legislation Explorer — Data Fix Plan

## Status Summary

| Act | Files Cleaned | Missing Sections | Duplicates | Unknown Divisions | Unknown Parts |
|-----|---------------|------------------|------------|-------------------|---------------|
| ITAA 1997 | 1,402 / 4,638 | 0 | 0 | 0 | 0 |
| ITAA 1936 | 1 / 1,013 | s168, s170 (fixed) | 7 | 81 | 0 |
| GST 1999 | 0 / 830 | s5-5, s45-1, s45-5 | 0 | 0 | 0 |
| TAA 1953 | 4 / 1,316 | 0 | 25 | 113 | 817 |

---

## Phase 1: Content Quality (PDF Artifact Cleanup)

### 1.1 ITAA 1997 — DONE
- **Problem:** Running headers concatenated to end of content lines (e.g. `Specialist liability rules Chapter 3 Part 3-3 Division 124 Section 124-780`).
- **Fix applied:** Regex stripping `\s+<Topic> Chapter N Part N Division N Section N$` from line ends.
- **Files modified:** 1,402
- **Verification:** `grep -r 'Specialist liability rules Chapter' data/itaa-1997/sections/` should return nothing.

### 1.2 ITAA 1936 — INCOMPLETE
- **Problem:** Only 1 file cleaned. PDF artifacts exist but have different patterns.
- **Root cause:** Cleanup regex tuned for ITAA 1997 topic-based headers. ITAA 1936 uses `Part IV Returns and assessments`, `Section 170`, page numbers like `211`, `Compilation No. 191`.
- **Fix needed:** Add ITAA 1936-specific patterns to cleanup script:
  - `Part [IVX]+ .*` running headers
  - `Section \d+[A-Z]?` inline headers
  - `Compilation No\. \d+` / `Compilation date: dd/mm/yyyy`
  - `Authorised Version C\d+ registered dd/mm/yyyy`
  - Right-aligned page numbers + act name
- **Deliverable:** Re-run cleanup on all 1,013 ITAA 1936 files. Target: >50% of files show improvements.

### 1.3 GST 1999 — NOT STARTED
- **Problem:** 0 files cleaned.
- **Fix needed:** Identify GST-specific PDF artifacts (likely similar to ITAA 1997 but with "A New Tax System (Goods and Services Tax) Act 1999" footers).
- **Deliverable:** Run targeted scan, add GST patterns, clean affected files.

### 1.4 TAA 1953 — INCOMPLETE
- **Problem:** Only 4 files cleaned.
- **Fix needed:** Same as above — act-specific artifact patterns.
- **Deliverable:** Re-run cleanup. Target: identify and clean all contaminated files.

### 1.5 Master Tax Examples — NOT STARTED
- **Problem:** Broken paragraphs mid-word (15 files detected in audit).
- **Fix needed:** Detect lines that end mid-word and next line starts with unrelated text; merge and strip.
- **Deliverable:** Fix all 15 broken paragraph instances.

---

## Phase 2: Missing Sections

### 2.1 ITAA 1936 s168 — DONE
- **Status:** Created at `data/itaa-1936/sections/part-iv/division-unknown/168.md`
- **Verification:** File exists, clean, tree.json updated.

### 2.2 ITAA 1936 s170 — DONE
- **Status:** Created at `data/itaa-1936/sections/part-iv/division-unknown/170.md` (30,480 chars, 460 lines)
- **Verification:** No PDF contamination. Ends correctly before s170A.
- **Tree update:** s168 and s170 inserted into tree.json Part IV.

### 2.3 GST 1999 s5-5, s45-1, s45-5 — NOT STARTED
- **Problem:** Sections exist in raw text but were not ingested into tree.json / .md files.
- **Root cause:** Parser regex `^Section (\d+)` failed because these sections lack the "Section" prefix in the raw text.
- **Fix needed:** Extract from raw text, create .md files, insert into tree.json.
- **Deliverable:** 3 new .md files + tree.json update.

---

## Phase 3: Structural Integrity

### 3.1 Duplicate Section IDs in tree.json
- **ITAA 1936:** 7 duplicates (e.g. section "1" appears multiple times in different parts).
- **TAA 1953:** 25 duplicates.
- **Fix:** Manually review duplicates. If they're genuinely different sections (same number, different letter suffix), rename IDs. If they're index/TOC entries, remove from tree.
- **Deliverable:** Zero duplicate IDs in tree.json.

### 3.2 `division-unknown` Paths
- **ITAA 1936:** 81 sections.
- **TAA 1953:** 113 sections.
- **Fix:** Where possible, map sections to correct divisions using raw text or legislation structure. Where division is truly not defined in the Act, keep as `division-unknown`.
- **Deliverable:** Correct divisions for all mappable sections.

### 3.3 `part-unknown` Paths
- **TAA 1953:** 817 sections (mostly Divisions 284–446, 355, 356, etc.).
- **Fix:** TAA 1953 Schedule 1 sections (Divisions 284+) don't map to traditional "Parts". May need a schema change (e.g. `part: "schedule-1"`).
- **Deliverable:** Decision on schema + update tree.json and all file paths.

---

## Phase 4: Commentary Panels (Frontend/API)

### 4.1 Problem
- User reports commentary not visible under sections.
- Backend loads 5,230 commentary items successfully.
- Direct API test returned empty response (backend may not be running, or endpoint wrong).

### 4.2 Debug Steps
1. Confirm backend is running (`curl http://127.0.0.1:8001/health` or equivalent).
2. Check browser devtools Network tab for the exact commentary API URL the frontend calls.
3. Verify the endpoint exists in `backend/main.py` or routers.
4. Test API manually with known-good keys.
5. Check if CORS is blocking the frontend.
6. Verify frontend renders the response correctly (null-checks, loading states).

### 4.3 Deliverable
- Commentary visible and populated for all sections that have data.

---

## Phase 5: Definition Linking

### 5.1 Problem
- Nested/broken links like `[[income tax](/itaa-1997/s995-1#s995-1-1-d) law]`.
- Already patched `backend/processors/markdown.py` with placeholder system.

### 5.2 Verification
- Check s1-3 (or any section with nested definitions) for correctly rendered links.
- Ensure no `[[term](url)]` patterns remain in processed output.

### 5.3 Deliverable
- All definition links render correctly without nesting.

---

## Execution Order

| Phase | Task | Priority | Effort | Status |
|-------|------|----------|--------|--------|
| 1.2 | ITAA 1936 PDF cleanup | High | Medium | Not started |
| 1.3 | GST 1999 PDF cleanup | High | Medium | Not started |
| 1.4 | TAA 1953 PDF cleanup | Medium | Medium | Not started |
| 1.5 | Master Tax Examples broken paragraphs | Low | Low | Not started |
| 2.3 | GST missing sections (s5-5, s45-1, s45-5) | High | Medium | Not started |
| 3.1 | Duplicate section IDs | Medium | High | Not started |
| 3.2 | Fix `division-unknown` paths | Medium | High | Not started |
| 3.3 | Fix `part-unknown` paths (TAA Schedule 1) | Medium | High | Not started |
| 4.x | Debug commentary API/panels | High | Medium | In progress |
| 5.x | Verify definition linking fix | Medium | Low | Done |

---

## Files Created During Audit

- `fix_all_data_issues.py` — Main cleanup + missing section script
- `data_quality_missing_sections.json` — Raw missing section candidates
- `data_quality_missing_sections_filtered.json` — Filtered to real issues
- `data_quality_missing_sections_summary.txt` — Text summary
- `data_quality_garbled_detailed.json` — Garbled content scan results
- `data_quality_structural_issues.json` — Structural audit results
- `DATA_QUALITY_AUDIT_PRD.md` — Original PRD
- `cleanup_garbled.py` — Earlier cleanup attempt
- `filter_missing_sections.py` — Missing section filter script
- `scan_legislation.py` — Garbled content scanner
- `audit_script.py` — Structural integrity checker

---

## Verification Checklist

- [ ] `grep -r 'Specialist liability rules Chapter' data/itaa-1997/sections/` returns empty
- [ ] `grep -r 'Compilation No\.' data/itaa-1936/sections/ | wc -l` < 10
- [ ] s168.md loads correctly in frontend
- [ ] s170.md loads correctly, no truncation, no PDF artifacts
- [ ] s5-5.md, s45-1.md, s45-5.md exist and load
- [ ] tree.json has zero duplicate section IDs
- [ ] Commentary panel shows content for s6-5
- [ ] No nested `[[term](url)]` links in rendered HTML
