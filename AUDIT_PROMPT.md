# Audit: MCP Bug Fixes Batch 2

Audit the following changes on branch `feature/bugfix-batch-jul27`. I need you to review all modified files for correctness, edge cases, and regressions.

## Files modified

### backend/services/data_loader.py

1. **`_check_withdrawn()`** — new helper that scans full content for withdrawal/supersession patterns (not just first 1000 chars). Check: patterns catch real ATO withdrawal language without false positives.
2. **`_strip_ato_chrome()`** — new helper that strips "Legal database / Contents / Download / Email / Print / Back to browse" boilerplate from ruling previews and content. Check: doesn't strip legitimate content.
3. **`get_definition_text()`** — major rewrite of the text-boundary detection. Replaced the 500-char cap with definition-boundary detection (next `####` heading, next `<a id="...">` anchor, next col-0 definition pattern). Added `truncated`, `is_cross_reference`, `text_length` fields. Check: the col-0 definition boundary regex doesn't fire too broadly and cut definitions short.
4. **`load_rulings()`** — both loops now use `_check_withdrawn()` and `_strip_ato_chrome()`. Second loop (ATO_RULING_DIR) now includes `full_title` and `withdrawn` fields. `source` path retained internally.

### backend/mcp_server.py

1. **`list_rulings` tool** — added `type`, `year`, `limit`, `offset`, `counts_only` params. Handler filters rulings before grouping. `counts_only` returns just the histogram. `withdrawn` field added to each entry.
2. **`get_act_tree` tool** — added `depth` param (`parts` | `divisions` | `sections`). `parts` returns only top-level part ids/titles (~31 rows for ITAA 1997 instead of 1.1M chars).
3. **`_get_ruling()`** — added `withdrawn` to response, strips ATO chrome from `content`.
4. **`search_legislation` tool description** — updated to reflect section-number ranking.

### backend/services/case_db_service.py

1. **`get_case_metadata()`** — `decision_date_note` field added: flags `-01-01` dates as year-only placeholders.
2. **`get_case_paragraphs()`** — `warning` field added: flags mid-sentence segmentation risk.
3. **`search_case_paragraphs()`** — snippet now centred on first match occurrence (150-char window each side) instead of `LEFT(300)`. `content` field fetched instead of hardcoded snippet SQL.
4. **`build_download_urls()`** — added `court_url` (HCA + FCA/FCAFC specific URLs), populated `content_length` from DB instead of hardcoded `None`.

### backend/services/search_service.py

1. **`search_sections()`** — section-number-shaped queries (e.g. `"8-1"`) now exact-match against section IDs and bubble the match to rank 1. Limited to `limit` results.

## What to check

- Do the regex patterns in `_check_withdrawn()` have false positives on words like "predecessor" (contains "superseded"?). "Superseded" should match but check "withdrawn" isn't matching "within" or "withdrawal" in a different context.
- Does `_strip_ato_chrome()` double-strip if called on already-stripped text?
- The `get_definition_text()` regex on line ~698: `r'\n(?=[A-Za-z][\w\s]*(?:means?|includes?|has\s+(?:the\s+)?same\s+meaning|:))'` — could this fire on a sentence like "This means the taxpayer..." mid-definition? The negative lookbehind protections from the original code were preserved but verify.
- Section-number regex `r'^(\d+[A-Z]?-\d+[A-Za-z]*(?:\(\d+\))?)$'` — what about sub-sub-sections like "40-25(2)" or "20-30(1)(a)"?
- The `counts_only` mode for `list_rulings` — is the histogram accurate when filters are applied?

Report any issues you find. Do NOT modify files — this is a read-only audit.
