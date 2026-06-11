# Data Quality Audit & Fix PRD

## Problem Statement
The legislation explorer ingestion pipeline has produced data with three known classes of errors. This PRD scopes a full audit, fix, and verification pass.

## Known Issue Classes

### Class A: Missing Sections
ITAA 1936 section 170 ("Amendment of assessments") exists in raw text but was not ingested. The parser's section-header regex likely misses bare-number headings like `170 Amendment of assessments` that lack a "Section" prefix. Need to audit all acts for similar gaps.

### Class B: PDF Header/Footer Leakage
Section 124-780 and others in Division 124 contain raw PDF page header/footer text mixed into legislative content, e.g.:
```
...that Specialist liability rules Chapter 3 Capital gains and losses:
special topics Part 3-3 Replacement-asset roll-overs Division 124
Section 124-780 company or members...
```
This garbles the operative text. Need to scan all sections for leaked headers/footers (patterns: "Chapter", "Part", "Division", "Section" + act name + page numbers + "Compilation").

### Class C: Broken Definition Linking (Fixed)
`auto_link_definitions` in `backend/processors/markdown.py` created nested markdown links when shorter defined terms matched inside longer-term links. Fix already applied using placeholders.

## Discovery Methodology

1. **Missing Sections Audit**
   - For each act, scan raw `.txt` files for section headers matching known patterns.
   - Cross-reference against `tree.json` section IDs.
   - Flag any section numbers found in raw text but missing from tree.

2. **Garbled Content Audit**
   - Scan all `.md` section files for leaked PDF artifacts:
     - Lines containing both a section number and "Chapter" or "Part" or "Division"
     - Lines containing "Compilation No." or "Compilation date:"
     - Lines containing act name mid-paragraph (not at start)
   - Flag files with contamination.

3. **Frontend/API Verification**
   - Confirm commentary/cases/rulings panels render correctly after data fixes.

## Fix Approach

1. **Missing Sections**
   - Update parser regexes to catch bare-number section headers.
   - Re-ingest affected raw volumes.
   - Or: manually create missing `.md` files from raw text and add to tree.

2. **Garbled Content**
   - Identify the exact header/footer patterns per volume.
   - Strip them from raw text or re-run ingestion with improved cleaners.
   - Re-generate affected `.md` files.

3. **Tree Rebuild**
   - After all fixes, rebuild `tree.json` for affected acts.

## Verification Criteria

- Every section referenced in raw text appears in `tree.json`.
- No `.md` file contains "Compilation No." or "Compilation date:" mid-body.
- No `.md` file contains consecutive act-name + chapter/part/division strings inside operative paragraphs.
- Section 170 renders correctly for ITAA 1936.
- Section 124-780 renders cleanly without header leakage.

## Files to Audit
- `/home/harrison/legislation-explorer/data/*/raw/*.txt`
- `/home/harrison/legislation-explorer/data/*/tree.json`
- `/home/harrison/legislation-explorer/data/*/sections/**/*.md`
- `/home/harrison/legislation-explorer/pipeline/parse_*.py`
