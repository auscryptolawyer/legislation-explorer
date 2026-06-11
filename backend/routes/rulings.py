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

@router.get("/api/rulings-list")
def list_rulings():
    rulings = load_rulings()
    # Group by year, then type
    years = {}
    for r in rulings:
        year = r.get("year", 0)
        t = r.get("type", "Ruling")
        if year not in years:
            years[year] = {}
        if t not in years[year]:
            years[year][t] = []
        years[year][t].append(r)
    # Build tree: Part=Year, Division=Type, Section=Ruling
    parts = []
    for year in sorted(years.keys(), reverse=True):
        divisions = []
        for t in sorted(years[year].keys()):
            # Sort sequentially by ruling number (e.g., TD 2022/1, TD 2022/2, TD 2022/10)
            def ruling_sort_key(r):
                m = re.search(r'(\d+)$', r["citation"])
                return int(m.group(1)) if m else 0
            sections = sorted(years[year][t], key=ruling_sort_key)
            divisions.append({
                "id": f"{year}-{t.lower().replace(' ', '-')}",
                "title": t,
                "subdivisions": [],
                "sections": [
                    {"id": r["citation"], "title": r["title"], "path": r["citation"]}
                    for r in sections
                ],
            })
        parts.append({
            "id": str(year),
            "title": str(year),
            "divisions": divisions,
            "sections": [],
        })
    return {"act": "ATO Rulings", "parts": parts}

@router.get("/api/ruling/{citation:path}")
def get_ruling(citation: str):
    citation = citation.replace("%20", " ")
    # Search in all ruling directories
    for r in load_rulings():
        if r["citation"] == citation:
            path = Path(r["source"])
            if path.exists():
                content = path.read_text(encoding="utf-8")
                referenced_sections = load_ruling_section_refs(citation)
                body = f"# {r['title']}\n\n**Type:** {r['type']}\n\n**Year:** {r['year']}\n\n---\n\n{content}"
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