from __future__ import annotations

import re
import logging

from fastapi import HTTPException, APIRouter

from backend.config import DATA_DIR, SEARCH_DB
from backend.services.data_loader import load_tree
from backend.services.search_service import search_conn, init_search_index as build_search_index, search_sections as fts_search

logger = logging.getLogger(__name__)
router = APIRouter()

SECTION_NUMBER_RE = re.compile(r'^[0-9]+(-[0-9]+)?$')


@router.get("/api/search")
def search(q: str, act: str | None = None, offset: int = 0, limit: int = 50):
    if limit > 100:
        limit = 100
    if offset < 0:
        offset = 0

    if not SEARCH_DB.exists():
        build_search_index()

    q = q.strip()
    all_results = []
    exact_row = None

    if SECTION_NUMBER_RE.match(q):
        with search_conn() as conn:
            if act:
                exact_row = conn.execute(
                    "SELECT act, section, title, part, division FROM sections_meta WHERE act = ? AND section = ?",
                    (act, q)
                ).fetchone()
            else:
                exact_row = conn.execute(
                    "SELECT act, section, title, part, division FROM sections_meta WHERE section = ?",
                    (q,)
                ).fetchone()

            if exact_row:
                all_results.append({
                    "act": exact_row["act"],
                    "section": exact_row["section"],
                    "title": exact_row["title"],
                    "part": exact_row["part"],
                    "division": exact_row["division"],
                    "exact_match": True,
                })

    try:
        fts_results = fts_search(q, act, limit=500)
        for r in fts_results:
            if exact_row and r["act"] == exact_row["act"] and r["section"] == exact_row["section"]:
                continue
            all_results.append(r)
    except Exception:
        logger.exception("FTS search failed")

    if not all_results:
        acts_to_search = [act] if act else [d.name for d in DATA_DIR.iterdir() if d.is_dir()]
        for a in acts_to_search:
            try:
                tree = load_tree(a)
            except HTTPException:
                continue
            q_lower = q.lower()
            for part in tree.get("parts", []):
                for sec in part.get("sections", []):
                    if q_lower in sec["id"].lower() or q_lower in sec.get("title", "").lower():
                        all_results.append({"act": a, "section": sec["id"], "title": sec.get("title", "")})
                for div in part.get("divisions", []):
                    for sec in div.get("sections", []):
                        if q_lower in sec["id"].lower() or q_lower in sec.get("title", "").lower():
                            all_results.append({"act": a, "section": sec["id"], "title": sec.get("title", "")})
                    for sub in div.get("subdivisions", []):
                        for sec in sub.get("sections", []):
                            if q_lower in sec["id"].lower() or q_lower in sec.get("title", "").lower():
                                all_results.append({"act": a, "section": sec["id"], "title": sec.get("title", "")})

    total = len(all_results)
    page = all_results[offset:offset + limit]
    engine = "fallback" if not SEARCH_DB.exists() else "fts5"
    return {"results": page, "total": total, "offset": offset, "limit": limit, "engine": engine}
