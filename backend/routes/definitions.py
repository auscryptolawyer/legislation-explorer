from __future__ import annotations

import logging
import re

from fastapi import HTTPException, APIRouter

from backend.services.data_loader import load_definitions, get_definition_text, get_act_section_content

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/definitions/{act}")
def get_definitions(act: str):
    defs = load_definitions(act)
    return {"act": act, "count": len(defs), "terms": defs}


@router.get("/api/definition/{act}/{term}")
def get_definition(act: str, term: str):
    result = get_definition_text(act, term)
    if not result:
        raise HTTPException(status_code=404, detail=f"Definition for '{term}' not found")
    return result


@router.get("/api/definition-text/{act}/{term}")
def get_definition_text_route(act: str, term: str):
    result = get_definition_text(act, term)
    if not result:
        raise HTTPException(status_code=404, detail=f"Definition for '{term}' not found")
    return result


@router.get("/api/section-defined-terms/{act}/{section}")
def section_defined_terms(act: str, section: str):
    """Return defined terms that appear in a section's body text."""
    try:
        fm, body = get_act_section_content(act, section)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error loading section content")
        return {"act": act, "section": section, "count": 0, "terms": []}

    if not body:
        return {"act": act, "section": section, "count": 0, "terms": []}

    defs = load_definitions(act)
    if not defs:
        return {"act": act, "section": section, "count": 0, "terms": []}

    body_lower = body.lower()
    found = []
    for term, info in defs.items():
        if term.lower() in body_lower:
            found.append({
                "term": term,
                "section": info.get("section", ""),
                "anchor": info.get("anchor", ""),
            })
    found.sort(key=lambda t: len(t["term"]), reverse=True)
    return {"act": act, "section": section, "count": len(found), "terms": found}
