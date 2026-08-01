"""API routes for Keays Insolvency textbook."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.config import INSOLVENCY_DIR
from backend.services.search_service import (
    search_insolvency as fts_search_insolvency,
    get_insolvency_chapter as get_chapter,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/insolvency/chapters")
def list_insolvency_chapters():
    """List all insolvency textbook chapters with titles."""
    import json
    ch_tree_path = INSOLVENCY_DIR / "ch-tree.json"
    if not ch_tree_path.exists():
        raise HTTPException(status_code=404, detail="Insolvency textbook not found")
    ch_tree = json.loads(ch_tree_path.read_text(encoding="utf-8"))
    return {"chapters": ch_tree.get("chapters", []), "total": ch_tree.get("total", 0)}


@router.get("/api/insolvency/chapter/{chapter}")
def get_insolvency_chapter(chapter: int):
    """Get full text of an insolvency textbook chapter by number."""
    result = get_chapter(chapter)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter} not found")
    return result


@router.get("/api/insolvency/search")
def search_insolvency(q: str, limit: int = 20):
    """Full-text search across insolvency textbook chapters."""
    if not q or not q.strip():
        return {"results": [], "total": 0, "query": q}
    from backend.services.search_service import init_search_index
    from backend.config import SEARCH_DB
    if not SEARCH_DB.exists():
        init_search_index()
    result = fts_search_insolvency(q.strip(), limit=min(limit, 50))
    return {"query": q, **result}
