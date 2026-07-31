from __future__ import annotations

import re
import logging

from fastapi import HTTPException, APIRouter

from backend.config import DATA_DIR, SEARCH_DB
from backend.services.data_loader import load_tree
from backend.services.search_service import search_conn, init_search_index as build_search_index, search_sections as fts_search, search_rulings
from backend.services import vector_search_service

logger = logging.getLogger(__name__)
router = APIRouter()

RRF_K = 60

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
        fts_results = fts_search(q, act, limit=500).get("results", [])
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


@router.get("/api/unified-search")
def unified_search(q: str, limit: int = 20):
    """Search legislation acts, CCH guides, rulings, and tax cases in one call, grouped by category."""
    from .acts import list_acts
    from .tax_cases import search_tax_cases

    q = q.strip()
    if not q:
        return {"query": q, "categories": []}

    categories = []
    for a in list_acts():
        act_id = a["id"]
        data = search(q, act=act_id, limit=limit)
        results = data.get("results", [])
        if results:
            categories.append({
                "key": act_id,
                "label": a["name"],
                "count": data.get("total", len(results)),
                "results": [
                    {"type": "section", "act": act_id, "section": r.get("section"), "title": r.get("title", "")}
                    for r in results
                ],
            })

    case_data = search_tax_cases(q, limit=limit)
    if case_data["results"]:
        categories.append({
            "key": "cases",
            "label": "Cases",
            "count": case_data["total"],
            "results": [
                {"type": "case", "citation": c.get("citation"), "title": c.get("title", ""), "court_label": c.get("court_label", "")}
                for c in case_data["results"]
            ],
        })

    return {"query": q, "categories": categories}


@router.get("/api/search/flat")
def search_flat(q: str, limit: int = 50):
    """Flat-ranked search across legislation sections AND rulings. Single FTS5 query, BM25 order."""
    q = q.strip()
    if not q:
        return {"query": q, "results": []}
    if not SEARCH_DB.exists():
        build_search_index()
    try:
        section_results = fts_search(q, act=None, limit=limit).get("results", [])
        ruling_results = search_rulings(q, limit=limit)

        # Interleave: take from both sources to show mixed results
        combined = []
        sec_idx = 0
        rul_idx = 0
        while len(combined) < limit and (sec_idx < len(section_results) or rul_idx < len(ruling_results)):
            if sec_idx < len(section_results) and (rul_idx >= len(ruling_results) or len(combined) % 2 == 0):
                r = section_results[sec_idx]
                sec_idx += 1
                combined.append({"type": "section", "act": r["act"], "section": r["section"], "title": r.get("title", ""), "snippet": r.get("snippet", "")})
            elif rul_idx < len(ruling_results):
                r = ruling_results[rul_idx]
                rul_idx += 1
                combined.append({"type": "ruling", "act": "rulings", "section": r["citation"], "title": r.get("title", ""), "snippet": r.get("snippet", "")})

        return {"query": q, "results": combined[:limit]}
    except Exception as e:
        logger.exception("Flat search failed")
        return {"query": q, "results": [], "error": str(e)}


@router.get("/api/search/hybrid")
def search_hybrid(q: str, act: str | None = None, limit: int = 20):
    if limit > 50:
        limit = 50

    q = q.strip()
    if not SEARCH_DB.exists():
        build_search_index()

    try:
        fts_results = fts_search(q, act, limit=50).get("results", [])
    except Exception:
        logger.exception("FTS search failed")
        fts_results = []

    try:
        vector_results = vector_search_service.search(q, limit=50)
    except Exception:
        logger.exception("Vector search failed")
        vector_results = []
    if act:
        vector_results = [r for r in vector_results if r["act"] == act]

    scores: dict[tuple[str, str], float] = {}
    merged: dict[tuple[str, str], dict] = {}

    for rank, r in enumerate(fts_results):
        key = (r["act"], r["section"])
        scores[key] = scores.get(key, 0.0) + 1 / (RRF_K + rank + 1)
        merged.setdefault(key, {**r, "embedding_id": None})

    for rank, r in enumerate(vector_results):
        key = (r["act"], r["section"])
        scores[key] = scores.get(key, 0.0) + 1 / (RRF_K + rank + 1)
        existing = merged.setdefault(key, {**r})
        existing.setdefault("embedding_id", r["embedding_id"])
        existing.setdefault("snippet", r["snippet"])

    ranked_keys = sorted(scores, key=lambda k: -scores[k])[:limit]
    results = []
    for key in ranked_keys:
        r = merged[key]
        r["fusion_score"] = scores[key]
        emb_id = r.get("embedding_id")
        r["cross_references"] = vector_search_service.get_cross_references(emb_id) if emb_id else []
        results.append(r)

    return {"results": results, "total": len(results), "q": q}
