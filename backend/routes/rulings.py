from __future__ import annotations

import json
import re
import logging
from pathlib import Path

from fastapi import HTTPException, APIRouter
from fastapi.responses import FileResponse, HTMLResponse

from ..config import RULING_DIR, ATO_RULING_DIR
from ..services.data_loader import (
    load_rulings, get_act_section_content, load_ruling_section_refs
)

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/api/rulings/{act}/{section}")
def rulings_for_section(act: str, section: str, limit: int = 50, offset: int = 0):
    from ..services.data_loader import get_rulings_for_section
    rulings = get_rulings_for_section(act, section, limit, offset)
    ruling_list = load_rulings()
    richer_rulings = []
    for r in rulings:
        found = next((item for item in ruling_list if item["citation"] == r["citation"]), None)
        if found:
            richer_rulings.append(found)
    return {
        "act": act,
        "section": section,
        "count": len(richer_rulings),
        "rulings": richer_rulings,
    }

TYPE_DISPLAY: dict[str, str] = {
    "AID": "ATO ID – ATO Interpretative Decision",
    "GSTR": "GSTR – GST Ruling",
    "IT": "IT – Income Tax Ruling",
    "LCG": "LCG – Law Companion Guideline",
    "MT": "MT – Miscellaneous Tax Ruling",
    "PCG": "PCG – Practical Compliance Guideline",
    "PS LA": "PS LA – Practice Statement (Law Administration)",
    "SGR": "SGR – Superannuation Guarantee Ruling",
    "TA": "TA – Taxpayer Alert",
    "TD": "TD – Tax Determination",
    "TR": "TR – Tax Ruling",
}

@router.get("/api/rulings-list")
def list_rulings(group: str = "year"):
    """
    List all ATO rulings grouped by year or by ruling type.

    Parameters:
    - group: "year" (default) → Year → Type → Rulings
            "type"           → Type → Year → Rulings
    """
    rulings = load_rulings()
    years = {}
    for r in rulings:
        year = r.get("year", 0)
        t = r.get("type", "Ruling")
        if year not in years:
            years[year] = {}
        if t not in years[year]:
            years[year][t] = []
        years[year][t].append(r)

    def ruling_sort_key(r):
        m = re.search(r'(\d+)$', r["citation"])
        return int(m.group(1)) if m else 0

    if group == "type":
        # Group: Type → Year → Rulings
        types: dict[str, dict] = {}
        for year, type_dict in years.items():
            for t, secs in type_dict.items():
                if t not in types:
                    types[t] = {}
                types[t][year] = secs

        parts = []
        for t in sorted(types.keys()):
            year_divs = []
            for year in sorted(types[t].keys(), reverse=True):
                sections = sorted(types[t][year], key=ruling_sort_key)
                year_divs.append({
                    "id": f"{t.lower().replace(' ', '-')}-{year}",
                    "title": str(year),
                    "subdivisions": [],
                    "sections": [
                        {
                            "id": r["citation"],
                            "title": r.get("citation_display", r["citation"]) + (f" — {r.get('full_title', '')}" if r.get('full_title') and r.get('full_title') != r["title"] and 'Legal database' not in r.get('full_title', '') else "") + ("  [WITHDRAWN]" if r.get('withdrawn') else ""),
                            "path": r["citation"],
                            "ato_url": r.get("ato_url", ""),
                            "austlii_url": r.get("austlii_url", ""),
                        }
                        for r in sections
                    ],
                })
            parts.append({
                "id": t.lower().replace(' ', '-'),
                "title": TYPE_DISPLAY.get(t, t),
                "divisions": year_divs,
                "sections": [],
            })
    else:
        # Default: Year → Type → Rulings
        parts = []
        for year in sorted(years.keys(), reverse=True):
            divisions = []
            for t in sorted(years[year].keys()):
                sections = sorted(years[year][t], key=ruling_sort_key)
                divisions.append({
                    "id": f"{year}-{t.lower().replace(' ', '-')}",
                    "title": TYPE_DISPLAY.get(t, t),
                    "subdivisions": [],
                    "sections": [
                        {
                            "id": r["citation"],
                            "title": r.get("citation_display", r["citation"]) + (f" — {r.get('full_title', '')}" if r.get('full_title') and r.get('full_title') != r["title"] and 'Legal database' not in r.get('full_title', '') else "") + ("  [WITHDRAWN]" if r.get('withdrawn') else ""),
                            "path": r["citation"],
                            "ato_url": r.get("ato_url", ""),
                            "austlii_url": r.get("austlii_url", ""),
                        }
                        for r in sections
                    ],
                })
            parts.append({
                "id": str(year),
                "title": "IT Rulings" if year == 0 else str(year),
                "divisions": divisions,
                "sections": [],
            })
    return {"act": "ATO Rulings", "parts": parts}

CITATION_ALIASES = {"LCR": "LCG"}

_ATO_ID_STRIP = re.compile(
    r'^(ATO\s+Interpretative\s+Decision\s*|ATO\s+ID\s+\d{4}/\d+\s*|=+\s*|File\s+Number\s*|FOI\s+status[^\\n]*|'
    r'This\s+ATO\s+ID[^\\n]*|This\s+document[^\\n]*)',
    re.IGNORECASE | re.MULTILINE
)

def _strip_ato_id_header(text: str) -> str:
    """Remove redundant header lines from ATO ID content (they duplicate page-level metadata)."""
    lines = text.splitlines()
    # Find first substantive line that isn't a header
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r'^(ATO\s+Interpretative\s+Decision|ATO\s+ID\s+\d{4}/\d+|={3,})$', stripped, re.IGNORECASE):
            continue
        if re.match(r'^(File\s+Number|FOI\s+status)', stripped, re.IGNORECASE):
            continue
        # First substantive line found
        return '\n'.join(lines[i:])
    return text

@router.get("/api/ruling/{citation:path}")
def get_ruling(citation: str):
    import re as _re
    citation = citation.replace("%20", " ")
    # Normalize: "TR 2020/1" → "TR_2020_1"
    normalized = _re.sub(r'[\s/]+', '_', citation).strip('_')
    candidates = {normalized}
    prefix_m = _re.match(r'^([A-Za-z]+)_(.*)$', normalized)
    if prefix_m and prefix_m.group(1).upper() in CITATION_ALIASES:
        candidates.add(f"{CITATION_ALIASES[prefix_m.group(1).upper()]}_{prefix_m.group(2)}")
    # Search in all ruling directories
    for r in load_rulings():
        if r["citation"] in candidates:
            path = Path(r["source"])
            if path.exists():
                content = path.read_text(encoding="utf-8")
                content = _strip_ato_id_header(content)
                referenced_sections = load_ruling_section_refs(citation)
                body = f"# {r.get('citation_display', r['title'])}\n\n**Type:** {TYPE_DISPLAY.get(r['type'], r['type'])}\n\n**Year:** {r['year']}\n\n---\n\n{content}"
                return {
                    "frontmatter": {
                        "act": "ATO Rulings",
                        "title": r["title"],
                        "part": r["type"],
                        "division": str(r["year"]),
                    },
                    "body": body,
                    "citation": r["citation"],
                    "type": r["type"],
                    "year": r["year"],
                    "referenced_sections": referenced_sections,
                }
    raise HTTPException(status_code=404, detail=f"Ruling {citation} not found")

@router.get("/api/ruling-sections/{citation:path}")
def get_ruling_sections(citation: str):
    citation = citation.replace("%20", " ")
    referenced_sections = load_ruling_section_refs(citation)
    
    sections_with_titles = []
    for ref in referenced_sections:
        act = ref["act"]
        section = ref["section"]
        
        try:
            fm, body = get_act_section_content(act, section)
            sections_with_titles.append({
                "act": act,
                "section": section,
                "title": fm.get("title", section),
                "full_title": fm.get("full_title", fm.get("title", section)),
            })
        except HTTPException as e:
            logger.warning(f"Could not retrieve content for {act} {section}: {e.detail}")
            sections_with_titles.append({
                "act": act,
                "section": section,
                "title": f"Section {section} (Title not found)",
                "full_title": f"Section {section} (Title not found)",
            })
    return {
        "citation": citation,
        "referenced_sections": sections_with_titles,
    }