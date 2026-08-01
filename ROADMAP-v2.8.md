# v2.8 — Cross-Domain Expansion

## Goal
Extend the Legislation Explorer beyond tax law into corporations law, AML/CTF, ASIC regulatory guidance, and insolvency — with namespace-prefixed tools to keep domains separate.

## Content Sources

### Corporations Act 2001
- ~3,000 sections across 10+ chapters
- PDF source format (ComLaw)
- Pipeline: PDF → markdown sections → tree.json → FTS5 → embeddings
- Acts: `corps-2001` (single act)
- Tool: `corps_get_section(section)`

### AML/CTF Act 2006
- ~300 sections
- PDF source format
- Same pipeline pattern
- Act: `aml-ctf-2006` (single act)
- Tool: `aml_get_section(section)`

### ASIC Rulings
- Regulatory guides, class orders, legislative instruments
- ~1,000+ documents
- Similar pipeline to ATO rulings (text/HTML)
- Tool: `asic_get_ruling(citation)`

### Keays Insolvency Textbook
- ~20-30 chapters
- Textbook format, not section-numbered legislation
- Better suited to full-text search rather than section lookup
- Tool: `insolvency_search(query)` or `insolvency_get_chapter(chapter)`

## Tool Namespacing

```
tax_get_section(act, section)        # existing: itaa-1997, itaa-1936, taa-1953, gst-1999
tax_get_ruling(citation)             # existing: ATO rulings
tax_search_all(query, type_filter)   # existing: tax-domain search

corps_get_section(section)           # Corporations Act 2001
aml_get_section(section)             # AML/CTF Act 2006
asic_get_ruling(citation)            # ASIC regulatory guides
insolvency_search(query)             # Keays textbook
insolvency_get_chapter(chapter)      # Keays textbook chapter

search_all(query, type_filter, act)  # cross-domain — add corps/aml/asic filters
```

## Pipeline Work

### New parsers needed:
- `pipeline/parse_corps_act.py` — extract sections from Corporations Act PDF
- `pipeline/parse_aml_ctf.py` — extract sections from AML/CTF Act PDF
- `pipeline/parse_asic_rulings.py` — scrape or parse ASIC rulings
- `pipeline/parse_keays.py` — extract chapters from Keays textbook

### Index rebuilds:
- `rebuild_search_index.py` — needs update to index new sources
- `build_cross_similarity.py` — needs update to compute cross-source embeddings

## Search Index

`search_all` should return results across all domains. The FTS5 index needs:
- A `domain` column (tax/corps/aml/asic/insolvency) for filtering
- Separate virtual tables or a unified schema

## Open Questions

- **Keays textbook format** — need to confirm source (PDF? ePub? scan?)
- **ASIC rulings format** — need to confirm whether structured JSON or raw text
- **Embeddings model** — does the current BGE model handle non-tax legal text well, or does it need domain-specific fine-tuning?
- **Tool naming** — prefix (`tax_`, `corps_`) vs parameterised (`get_section(domain="tax", act="itaa-1997")`)

## Status
- [ ] Corporations Act 2001 — pipeline
- [ ] AML/CTF Act 2006 — pipeline
- [ ] ASIC rulings — ingestion
- [ ] Keays insolvency — ingestion
- [ ] Tool namespace refactor
- [ ] search_all cross-domain update
- [ ] FTS5 index rebuild for new sources
- [ ] Embeddings similarity for new sources
