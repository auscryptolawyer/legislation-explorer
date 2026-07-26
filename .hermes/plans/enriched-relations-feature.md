# Enriched Relational Data Display

**Status:** Future Feature / Spec

## Goal

Show cross-references between content types as expandable sections at the bottom of every page. Each content type lists its relations to the other types.

## Relation Map

| Content Type | Shows Relations To |
|---|---|
| **Section** (legislation) | Cases, Rulings, Master Tax Guide |
| **Case** | Sections, Rulings, Master Tax Guide |
| **Ruling** | Sections, Master Tax Guide |

## Data Sources (Existing)

| Relation | Source |
|---|---|
| Section → Rulings | `/api/rulings/{act}/{section}` — returns rulings referencing a section |
| Section → Cases | `/api/section-tax-cases/{act}/{section}` — returns cases citing a section |
| Section → MTG | `/api/commentary/{act}/{section}` — returns MTG headings referencing a section |
| Case → Sections | `/api/tax-cases/case/{citation}/paragraphs?section_types=legislation` — paragraph-level section refs |
| Case → Rulings | Not yet indexed. Need: `case_citation_index.json` or inline refs in case body |
| Case → MTG | Not yet indexed. Need: cross-ref from case citator to master guide |
| Ruling → Sections | `/api/ruling-sections/{citation}` — returns legislation sections cited |
| Ruling → MTG | Not yet indexed. Need: cross-ref from ruling citator to master guide |

## UI Design

Each relation type is an expandable accordion collapsible at the bottom of the content page. The accordion shows a count + label, and when expanded, lists each item with its citation and title as a clickable link.

```
┌────────────────────────────────────────┐
│ ▼ Related Cases (3)                    │
│                                        │
│   • Commissioner v Smith [2024] HCA 12 │
│   • Re Jones [2023] AATA 45            │
│   • Brown & Co [2023] FCA 789          │
└────────────────────────────────────────┘
┌────────────────────────────────────────┐
│ ▶ Related Rulings (2)                  │
└────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Backend — Gather All Relations

1. **Case → Rulings index**: Parse case text for `TR \d{4}/\d+` / `TD \d{4}/\d+` / `ATO ID \d+` patterns; store in `data/case_ruling_refs.json`
2. **Ruling → MTG index**: Parse ruling section refs against commentary index; store in `data/ruling_commentary_index.json`
3. **Case → MTG index**: Cross-reference case-parsed section refs against commentary index
4. Create a unified API endpoint: `GET /api/relations/{type}/{id}` that returns all relation types for the given item

**Endpoint spec:**
```json
GET /api/relations/section/itaa-1997/s8-1
{
  "type": "section",
  "id": "itaa-1997/s8-1",
  "relations": {
    "cases": [{ "citation": "...", "title": "..." }],
    "rulings": [{ "citation": "...", "title": "..." }],
    "master_tax_guide": [{ "paragraph": "...", "title": "..." }]
  }
}
```

### Phase 2: Frontend — Accordion Component

Create a `RelationAccordion` component:
- Props: `type` (section/case/ruling), `id`, existing relation data
- Fetches from `/api/relations/{type}/{id}` if not pre-loaded
- Renders collapsible sections per relation type
- Items are clickable links that navigate within the app

### Phase 3: Integration

- Add `<RelationAccordion>` to `SectionContent`, `TaxCaseDetail`, and `RulingContent` lazy-loaded components
- Show below the main content, above the footer
- Styled consistently with existing collapsible panels (commentary, rulings panels)

## Data Pipeline

For the missing indexes, add pipeline scripts:

1. `pipeline/build_case_ruling_index.py` — parse case text files from CASE_DIR for ruling citation patterns
2. `pipeline/build_ruling_commentary_index.py` — cross-reference ruling sections against `_load_commentary_index()`

Both output to `data/*.json` files loaded via `@functools.lru_cache` in the data_loader.

## Edge Cases

- **Empty relations**: Show nothing (don't render the accordion section)
- **Loading state**: Show skeleton/loading text while fetching
- **Error state**: Silently hide relation sections that fail to load (don't break the page)
- **Nested relations**: No infinite expansion — sections link to other sections via existing navigate handler

