from __future__ import annotations

import re

from fastapi import HTTPException, APIRouter

from backend.services.data_loader import (
    load_definitions,
    get_definition_text,
    get_definition_across_acts,
)

router = APIRouter()


@router.get("/api/definitions/{act}")
def get_definitions(act: str):
    defs = load_definitions(act)
    return {"act": act, "count": len(defs), "terms": defs}


@router.get("/api/definition/{act}/{term}")
def get_definition(act: str, term: str):
    # Return the term wherever it is defined, preferring the requested act.
    result = get_definition_across_acts(term, preferred_act=act)
    if not result:
        raise HTTPException(status_code=404, detail=f"Definition for '{term}' not found")
    return result


@router.get("/api/definition-text/{act}/{term}")
def get_definition_text_route(act: str, term: str):
    result = get_definition_text(act, term)
    if not result:
        raise HTTPException(status_code=404, detail=f"Definition for '{term}' not found")
    return result
