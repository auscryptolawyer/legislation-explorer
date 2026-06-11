from __future__ import annotations

import re

from fastapi import HTTPException, APIRouter

from backend.services.data_loader import load_definitions, get_definition_text

router = APIRouter()


@router.get("/api/definitions/{act}")
def get_definitions(act: str):
    defs = load_definitions(act)
    return {"act": act, "count": len(defs), "terms": defs}


@router.get("/api/definition/{act}/{term}")
def get_definition(act: str, term: str):
    defs = load_definitions(act)
    key = term.lower()
    if key in defs:
        return defs[key]
    slug = re.sub(r"[^a-z0-9\s-]", "", key).strip()
    slug = re.sub(r"\s+", "-", slug)
    for k, v in defs.items():
        if v.get("anchor") in (f"s995-1-{slug}", f"s6-{slug}"):
            return v
    raise HTTPException(status_code=404, detail=f"Definition for '{term}' not found")


@router.get("/api/definition-text/{act}/{term}")
def get_definition_text_route(act: str, term: str):
    result = get_definition_text(act, term)
    if not result:
        raise HTTPException(status_code=404, detail=f"Definition for '{term}' not found")
    return result
