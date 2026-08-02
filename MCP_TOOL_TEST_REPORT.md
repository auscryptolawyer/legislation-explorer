# Cadena MCP (Legislation Explorer) v2.7.2 — Tool Test Report

**Date:** 2026-08-01
**Scope:** Black-box functional testing of all 16 live MCP tools on server `Cadena_MCP_V2_7_2`, cross-referenced against repo source (`backend/services/*`) where relevant.
**Method:** Happy-path + edge-case probing per tool. One real issue was filed via `report_issue` (**CDN-0038**) to exercise that tool.

> Note: the live v2.7.2 server (`fastmcp_server.py` per the in-server known-issue notes) is **not** in this repo snapshot; the repo's `backend/mcp_server.py` is an older variant with a different tool set. Fixes must be made against the deployed `fastmcp_server.py` / `data_loader.py` / `case_db_service.py`.

---

## Severity summary

| ID | Sev | Tool(s) | One-liner |
|----|-----|---------|-----------|
| B1 | HIGH | get_section | `related.commentary` embeds full commentary text → 100 KB+ responses, exceeds token limit even for tiny sections |
| B2 | HIGH | get_section | s 995-1 returns the entire 309 KB dictionary body; no pagination |
| B3 | HIGH | get_definition | Next-term boundary detection unreliable; "net capital gain" dumps 566 definitions (110 KB) to end-of-dictionary. CDN-0007 not fixed |
| B4 | HIGH | get_ruling | 2-digit-year citations (ATO's own format, e.g. `TR 97/7`) fail; only 4-digit `TR 1997/7` works |
| B5 | HIGH | search_cases | Case-name query ("Myer Emporium") does not surface the matching case at all; ranking broken |
| B6 | HIGH | case_legislation_refs | Wrong Act attributed (Part IVA provisions labelled ITAA 1997); get_case applies a correction this tool omits |
| B7 | MED | get_section | s 269-15(2A) still truncated + stray footnote spliced in — CDN-0006 "fix" not effective |
| B8 | MED | get_case | Structured `legislation_refs` mis-attributes Act (duplicate ITAA-1997 rows for 1936 sections). CDN-0008 partial |
| B9 | MED | get_case | AI-summary `cases_cited` citation→name pairs are wrong/hallucinated |
| B10 | MED | get_definition | Core terms missing: GST `supply`/`taxable supply`, ITAA97 `arm's length` |
| B11 | MED | get_ruling | ATO-ID `legislation_referenced` mangled — sentence fragments used as act titles |
| B12 | MED | insolvency_get_chapter | Full chapter (138 KB) exceeds token limit; no pagination |
| B13 | LOW | list_acts / get_act_tree | Bogus `compilation_no: 1` for taa-1953, master-tax-guide, master-tax-examples (section footers say 222) |
| B14 | LOW | get_act_tree | Part/division titles truncated (e.g. Part II "Commissioner of Taxation, Second") |
| B15 | LOW | get_case | `decision_date` defaulted to Jan-1 though real date is in the summary |
| B16 | LOW | get_case | `case_citations[].cited_case_name` always null (name present in context) |
| B17 | LOW | get_ruling | Type label inconsistent: "Tax Ruling" vs "Taxation Ruling" for same TR series |
| B18 | LOW | search_all / list_rulings | Ruling results use citation as `title` (no descriptive title) |
| B19 | LOW | search_cases / search_all | Metadata gaps (empty case_name/court with has_summary=true) |
| B20 | LOW | get_section | Commentary `section_refs` malformed ("s 188-15(1)(", "s 9-30)") |
| B21 | LOW | report_issue | Dedup returns same ticket but `duplicate_of: null`, no hit signal |
| B22 | LOW | get_info | `cases_in_db` (7375) < `cases_with_summaries` (8468) — inconsistent counts |
| B23 | HIGH | report_issue | Dedup **over-matches**: 20 distinct reports (different tool/params/category) all collapsed into one existing open ticket (CDN-0038) instead of creating new tickets |

### B23 — report_issue dedup collapses unrelated reports (filing is unreliable)
Attempting to file the 21 findings above as separate tickets, **20 of 21 returned the same ticket `CDN-0038`** (the earlier net-capital-gain report) despite differing in tool, params, and category. Only B7 (get_section / s 269-15 truncation) matched a genuine known issue (`CDN-0006`, status `known`). So new distinct findings are **not** being recorded as new tickets — the `(param_hash, category)` dedup is matching everything to the most recent open ticket (likely `param_hash` is not derived from the actual `params`/`tool`, so it is constant within a session/token).
**Impact:** `report_issue` cannot be relied on to capture multiple bugs — they silently merge into one ticket. This is why this report (committed to the repo) is the authoritative record rather than the issue tracker.
**Fix:** compute `param_hash` from a canonical serialization of `{tool, params}` and include `tool` in the dedup key; only match `known` seed issues by explicit rule.

---

## HIGH severity — details

### B1 — get_section response bloat from full commentary
`get_section` embeds the **full text** of related commentary paragraphs in `related.commentary[].content_blocks`.
- `get_section(itaa-1997, 8-1)`: body is 1,624 chars but total response = **121,852 chars** (commentary alone = 106 KB across 10 items) → *"exceeds maximum allowed tokens"*.
- `get_section(gst-1999, 9-5)`: single `¶4-020` commentary block is a full guide chapter (~10 KB) inlined.
**Fix:** return commentary as snippet + locator (publication/paragraph_number), not full `content_blocks`; add an `include_commentary`/limit param.

### B2 — get_section on s 995-1 returns the whole dictionary
`get_section(itaa-1997, 995-1)` returns a **309 KB body** (entire definitions section) → 438 KB response, token-limit error. Same risk for other very large sections. **Fix:** paginate large section bodies, or redirect callers to `get_definition`.

### B3 — get_definition boundary detection unreliable (CDN-0007 regressed)
The next-term boundary is not reliably found:
- `net capital gain` → **110,806 chars, 566 definitions**, running from the target term to the last dictionary entry `zero-capital amount` (s 820-942). `truncated:false`, `text_length:110806` — the tool believes this is the single definition.
- `market value` → returns its own def **plus** the next 3 terms (`market value method`, `maximum allowable debt`, `maximum available release amount`).
- Contrast: `CGT asset` (49 chars) and `taxable income` (156 chars) are correct.
Filed as **CDN-0038**. **Fix:** boundary lookup likely fails when the following term has a leading `*`/`- ` marker or isn't in the index, defaulting to end-of-section; normalize term keys before the alphabetical boundary comparison.

### B4 — get_ruling rejects 2-digit-year (canonical ATO) citations
`TR 97/7` and `TR_97_7` → not found, but `TR 1997/7` works — and the successful result's own `citation` field is **`"TR 97/7"`**. The ATO's canonical form for pre-2000 rulings *is* the 2-digit year, so the tool can't round-trip its own display citation. Affects the whole 1992–1999 corpus. The `did_you_mean` fallback returned irrelevant AIDs. **Fix:** in the normalizer, expand 2-digit years (`\d{2}` → `19xx/20xx`) and/or index by `citation_display`.

### B5 — search_cases ranking broken for case-name queries
`search_cases("Myer Emporium")` → 152 results, **none** of which is *FCT v Myer Emporium Ltd* `[1987] HCA 18` (confirmed present via `get_case`); top hits are unrelated (ICI Australia, Burness, TNT Skypak). By contrast `search_all(type_filter=case, "Myer Emporium")` **does** surface Myer-named cases in the top 5 — so the two case-search backends are inconsistent and `search_cases` name matching/ranking is the broken one. CDN-0003 (title added to haystack) is insufficient. **Fix:** rank exact/substring `case_name` matches first; align `search_cases` with the `search_all` backend.

### B6 — case_legislation_refs attributes the wrong Act
For `[1996] HCA 34` (Spotless), `case_legislation_refs` labels `s.177F`, `s.177D`, `s.177A(5)` as **"Income Tax Assessment Act 1997"** — all are ITAA 1936 Part IVA. `get_case` returns the *same* refs correctly as **"Income Tax Assessment Act 1936"** with `_act_corrected: true`. So the act-correction pass in `get_case` is **not applied** in `case_legislation_refs`. This is dangerous on a legal-citation tool. **Fix:** route both tools through the same corrected reference builder.

---

## MED severity — details

### B7 — s 269-15(2A) still truncated (CDN-0006 ineffective)
`get_section(taa-1953, 269-15)` (2A) still reads:
> "...an obligation to pay the amount of an estimate of an underlying liability under \n*For definition, see section 995-1 of the Income Tax Assessment Act 1997."

The restored text CDN-0006 claims ("Division 268, a director is subject to his or her obligation under subsection (1):") is absent, and a stray `*For definition…` footnote is spliced mid-subsection. The RE_NOISE footnote stripper isn't catching this indented case.

### B8 — get_case structured legislation_refs mis-attribution (CDN-0008 partial)
`[1987] HCA 18` (Myer) lists `s.25(1)/s.26(a)/s.260` under **both** ITAA 1936 (correct) and ITAA 1997 (wrong — those sections don't exist in the 1997 Act). Also `s.23(q)` stays ITAA 1997 even after `_act_corrected` in Spotless.

### B9 — AI-summary cases_cited names wrong/hallucinated
In `[1987] HCA 18`, `summary.cases_cited` maps e.g. `[1970] HCA 39 → "Lordianto v Cmr AFP"` (context: *McClelland v FCT*), `[1934] HCA 35 → "Roy Morgan Research Pty Ltd"` (a modern company), `[1936] HCA 11 → "FCT v Bargwanna"` (context: *Cmr of Taxes (Vic) v Phillips*). Citation→name pairing in summaries is unreliable — hazardous for legal use.

### B10 — get_definition misses core terms
Not found: `gst-1999 supply`, `gst-1999 taxable supply` (both defined in s 195-1), `itaa-1997 arm's length` / `arms length` (CDN-0001, still open). `enterprise` (GST) and most ITAA97 terms work — so the dictionary is only partially indexed.

### B11 — ATO-ID legislation_referenced mangled
`get_ruling("AID 2002/613")` returns `legislation_referenced` entries like *"ITAA 1936 does not apply (Cth) s 177EA"* and *"ITAA 1936 is directed to franking credit trading … cannot fully use them (Cth) s 177EA"* — sentence fragments captured as act titles. (`full_text` inline works correctly.)

### B12 — insolvency_get_chapter exceeds token limit
`insolvency_get_chapter(1)` = 137,996 chars → token-limit error. Chapters are inherently large; no pagination/offset param. Bounds handling is good (`0`, `22` → clean "not found").

---

## What passed (works well)
- `get_info`, `list_acts`, `list_rulings` (counts/filtered), `standards` (list + topics).
- `get_section` happy paths (177D, 6-5, 8-5, GST 9-5) and alias handling ("section 6-5"); wrong-format errors are excellent (itaa-1936 "6-1" → helpful cross-act `did_you_mean`).
- `get_definition` for well-behaved terms (CGT asset, ordinary income, taxable income, trading stock, enterprise).
- `get_ruling` for TR/PCG/LCR (incl. `LCR→LCG` alias) and 4-digit/underscore forms; ATO-ID `full_text` inline.
- `get_case` bracketed lookups, `include`/`search` full-text search (Part IVA → 3 hits with sentence context), rich cited_by/citations; clean not-found + hints for bad citations/underscore form.
- `case_legislation_refs` structure (aside from B6 act attribution).
- `search_legislation` (exact section-number ranking for "8-1"; empty result clean), `search_all` grouping + `type_filter`, `insolvency_search` snippets.
- `report_issue` creates tickets and dedups by param_hash (no duplicate ticket on repeat) — see B21 for the minor reporting gap.

---

## Recommended fix order
1. **B3, B1, B2, B12** — response-size / correctness blockers that make tools error out or return unusable blobs.
2. **B4** — pre-2000 ruling lookups (large corpus) currently unreachable by canonical citation.
3. **B5, B6, B8** — legal-accuracy defects (case findability, wrong Act on citations).
4. **B7, B10, B11, B9** — data-quality / parser fixes.
5. Remaining LOW items — metadata/labelling polish.
