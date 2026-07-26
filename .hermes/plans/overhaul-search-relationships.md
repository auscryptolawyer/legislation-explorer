# Search & Relationships Overhaul

## 1. Section display format
**Everywhere** (search results, related sections, rulings list, cases list):
`[SHORT ACT] s[SECTION]` → e.g. `ITAA97 s31-10`, `GST99 s195-1`, `TAA53 s2-1`

Short act mapping:
- `itaa-1997` → `ITAA97`
- `itaa-1936` → `ITAA36`
- `gst-1999` → `GST99`
- `taa-1953` → `TAA53`
- `master-tax-guide` → `CCH MTG`
- `master-tax-examples` → `CCH Example`
- `master-gst-guide` → `CCH GST`
- `nz-it-2007` → `NZ IT07`

Files: frontend side, search results, related content components, SectionContent, TreeNode.

## 2. Search improvements
- **Semantic/vector search** — `/api/search/hybrid` exists, frontend only uses `/api/search`. Add toggle for "Hybrid search" or boost semantic results.
- **Sort by relevance** — filter buttons on search results: "Best match", "Act (ITAA97 first)", "Section number"
- **Source filter** — checkbox list of acts to filter search results
- **MCP search tool** — register `search_legislation` as an MCP tool

## 3. Relationships / Related content
- **Commentary dropdown** — it exists but is empty. Check `/api/commentary/{act}/{section}` — may be data not loaded or endpoint returning empty. Fix data population.
- **Related sections** — sections that reference each other (cross-references). `/api/section-refs/{act}/{section}` exists — wire this into the related content panel.
- **Related rulings/cases** — already have dropdowns for these. Need to verify data.
- **All related under one "Related" panel** — combine commentary, section refs, rulings, cases into a single collapsible section.

## 4. Definitions
- **Same-act scope** — definitions endpoint currently returns ALL definitions. Restrict to the act the user is viewing.
- **Defined terms in section** — extract definition references from section content and show them under related content as clickable links.
- **Definition accuracy** — check that definition-text endpoint returns correct text for each term.

## 5. Visual graph explorer
- Clickable graph under a piece of content showing: the section, its definitions, related cases, related rulings, commentary
- Simple force-directed graph or radial tree
- SVG/Canvas rendering in a modal
- Click a node → navigate to that section/case/ruling

## Order of work
1. Short act display format (visual change, easy win)
2. Definitions fix (backend + frontend)
3. Search improvements (sorting, filtering, MCP tool)
4. Related content panel (combine all relationships)
5. Graph explorer (nice to have, last)