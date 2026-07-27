# MCP Tool Test — All 14 Tools

## Setup

Your MCP token is at https://legislation.scriptkitty.yachts/settings

First, add the MCP server to your Claude Code config:

```bash
cat >> ~/.claude/settings.local.json << 'EOF'
{
  "mcpServers": {
    "legislation-explorer": {
      "url": "https://legislation.scriptkitty.yachts/mcp?token=YOUR_TOKEN_HERE"
    }
  }
}
EOF
```

Now test every tool in order. Check each result before moving to the next.

---

### 1. list_acts

`mcp__legislation-explorer__list_acts`

Expected: ~30+ acts including itaa-1997, itaa-1936, taa-1953, rulings.

---

### 2. get_info

`mcp__legislation-explorer__get_info`

Expected: version, changelog, and "mcp_tool_count": 14.

---

### 3. get_act_tree

`mcp__legislation-explorer__get_act_tree` with `{"act": "itaa-1997"}`

Expected: full tree — Parts → Divisions/Subdivisions → Sections. Includes section 6-1, 8-1, etc.

---

### 4. search_legislation

`mcp__legislation-explorer__search_legislation` with `{"query": "taxable income", "act": "itaa-1997", "limit": 5}`

Expected: up to 5 results with `act`, `section`, `heading`, `snippet` each.

Note: AND matching — all query terms must appear in the text.

---

### 5. get_section

`mcp__legislation-explorer__get_section` with `{"act": "itaa-1997", "section": "6-1"}`

Expected: full body text of s 6-1 (income according to ordinary concepts).

---

### 6. get_definition

`mcp__legislation-explorer__get_definition` with `{"act": "itaa-1936", "term": "dividend"}`

Expected: primary definition — "dividend includes: (a) any distribution made by the company to any of its shareholders..."

Fixed bug: should NOT return the demerger sub-definition. Verify the returned text is the primary definition.

---

### 7. get_rulings_for_section

`mcp__legislation-explorer__get_rulings_for_section` with `{"act": "itaa-1997", "section": "8-1"}`

Expected: list of rulings citing s 8-1, each with citation, title, URLs.

---

### 8. list_rulings

`mcp__legislation-explorer__list_rulings` with `{}`

Expected: rulings grouped by year → type. Inspect the `full_title` values.

Fixed bug: titles should be descriptive (e.g. "Eligible termination payment: Extension of Time to Roll Over") NOT "AID_2001_1" placeholders. Check a few AID entries specifically.

---

### 9. get_ruling

`mcp__legislation-explorer__get_ruling` with `{"citation": "TR 2020/1"}`

Expected: full ruling metadata + content (the actual body text).

---

### 10. search_cases

`mcp__legislation-explorer__search_cases` with `{"query": "Bywater Investments", "limit": 5}`

Expected: Bywater Investments Ltd v Commissioner of Taxation [2016] HCA 45 in results.

---

### 11. get_case

`mcp__legislation-explorer__get_case` with `{"citation": "[2016] HCA 45"}`

Expected: case metadata + structural outline (HISTORY, FACTS, ARGUMENT, REASONING, etc.).

Also test party-name alias: try `"Bywater Investments Ltd v Commissioner of Taxation [2016] HCA 45"` — should work and return the same case.

---

### 12. get_case_paragraphs

`mcp__legislation-explorer__get_case_paragraphs` with `{"citation": "[2016] HCA 45", "section_types": ["FACTS"], "paragraph_limit": 5}`

Expected: first 5 paragraphs from the FACTS section, each with seq, type, content_md.

---

### 13. search_case_paragraphs

`mcp__legislation-explorer__search_case_paragraphs` with `{"query": "capital gains", "limit": 5}`

Expected: up to 5 paragraph results across all cases mentioning "capital gains", each with case citation, section type, snippet.

Note: uses exact-phrase matching (not keyword AND). Omit stopwords.

---

### 14. download_case

`mcp__legislation-explorer__download_case` with `{"citation": "[2016] HCA 45"}`

Expected: austlii_url and court_url for the full case PDF/HTML.

---

## Verification Checklist

- [ ] Tool 1 — ~30+ acts shown
- [ ] Tool 2 — version returned, 14 tools listed
- [ ] Tool 3 — tree has Parts → Divisions → Sections
- [ ] Tool 4 — results with snippet text
- [ ] Tool 5 — full body of s 6-1 returned
- [ ] Tool 6 — dividend definition is primary, NOT demerger sub-def
- [ ] Tool 7 — rulings citing s 8-1 returned
- [ ] Tool 8 — AID entries have real descriptive titles, not "AID_20XX_X"
- [ ] Tool 9 — TR 2020/1 has content (body text)
- [ ] Tool 10 — Bywater Investments found
- [ ] Tool 11 — metadata + sections returned; party-name alias works too
- [ ] Tool 12 — FACTS paragraphs returned
- [ ] Tool 13 — "capital gains" hits across cases
- [ ] Tool 14 — download URLs returned

Report any tool that returns an error or unexpected result.
