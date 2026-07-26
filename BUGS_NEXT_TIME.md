# Bugs to Fix Next Time (v2.1.1)

## 1. `get_rulings_for_section` returns `"year": 0` on every ruling

The v2.1.0 changelog says the year field was fixed "for all ruling types", but the fix only reached `get_ruling` (which correctly returns 2019, 2024, 2021). The list endpoint was missed.

**Server:** `backend/routes/rulings.py` — the `list_rulings_for_section` endpoint (or equivalent).

## 2. `get_ruling` doesn't normalise LCR → LCG

`LCR 2021/3` returns not-found, but the identical document resolves under `LCG_2021_3`. "LCR 2021/3" is both the ATO public citation and the exact title that `get_rulings_for_section` displays, so anyone copy-pasting a surfaced citation hits a dead end. Likely affects all Law Companion Rulings.

**Root cause:** The ATO publishes as "LCR" but files are stored with "LCG" prefix. The citation normalisation (`re.sub(r'[\s/]+', '_', citation)`) in `get_ruling` needs a mapping/alias table: `LCR → LCG`.

## 3. `get_definition` only resolves ITAA 1997 s 995-1

The tool accepts an `act` parameter but cannot resolve definitions in other acts:
- ITAA 1936 "dividend" (defined in s 6(1)) → not-found
- GST Act "enterprise" (s 195-1) → not-found

GST 195-1 is a known pre-existing data format limitation (definitions run together on blockquote lines, not clean col-0 entries like ITAA 1997 995-1).

The ITAA 1936 dictionary gap is newly surfaced — needs investigation.

## 4. Compilation metadata mismatch (GST)

`get_section gst-1999 9-5` footer reads:
> **Compilation 96** (2026-01-01)

But `list_acts` reports GST at:
> **Compilation 228** (2026-04-01)

The section footer and the act index disagree. Which one is stale?

---

### See also: pre-existing GST 195-1 limitation

The GST definitions file (`195-1.md`) has definitions that run together on blockquote lines instead of clean col-0 entries. This is a data extraction issue, not a tool logic bug, but it blocks `get_definition` for GST terms.
