"""Graph data endpoint — returns nodes + edges for force-directed visualization.

Supports three source types:
  - section:  /api/graph/data?type=section&act=itaa-1997&section=8-1
  - ruling:   /api/graph/data?type=ruling&citation=TR%202025/1
  - case:     /api/graph/data?type=case&citation=[2015]%20HCA%2048

Returns { nodes: [{id, label, group, url}], edges: [{source, target, label}] }
where group controls colour: section, ruling, case, definition, commentary.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import re as _re
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from backend.config import BASE

logger = logging.getLogger(__name__)

router = APIRouter()

EMBEDDINGS_DB = BASE / "data" / "embeddings.db"

RULING_TYPE_LABELS = {
    "TR": "Taxation Ruling",
    "TD": "Taxation Determination",
    "PCG": "Practical Compliance Guideline",
    "CR": "Class Ruling",
    "PS_LA": "Public Ruling (PS LA)",
    "SMSF": "SMSF Ruling",
    "IT": "Income Tax Ruling",
    "GSTR": "Goods & Services Tax Ruling",
    "LCR": "Low-Cost Ruling",
    "LCG": "Low-Cost Guideline",
    "ATOID": "ATO ID",
}

# ── helpers ──────────────────────────────────────────────────────────────────


def _section_url(act: str, section: str) -> str:
    return f"/sections/{act}/{section}"


def _ruling_url(citation: str) -> str:
    return f"/rulings/{citation.replace('/', '_').replace(' ', '/')}"


def _case_url(citation: str) -> str:
    from urllib.parse import quote
    return f"/tax-cases/{quote(citation)}"


# ── load rulings index from JSON ─────────────────────────────────────────────

_RULINGS_INDEX: dict[str, dict] | None = None


def _load_rulings_index() -> dict[str, dict]:
    """Load the rulings flat list for quick citation → title lookup."""
    global _RULINGS_INDEX
    if _RULINGS_INDEX is not None:
        return _RULINGS_INDEX
    path = BASE / "data" / "rulings" / "rulings_list.json"
    if path.exists():
        with open(path) as f:
            rulings = json.load(f)
        _RULINGS_INDEX = {}
        for r in rulings:
            key = r.get("citation", "").replace(" ", "").replace("_", "").upper()
            _RULINGS_INDEX[key] = r
    else:
        _RULINGS_INDEX = {}
    return _RULINGS_INDEX


_CASES_INDEX: dict[str, dict] | None = None
_SECTION_CASE_INDEX: dict[str, list] | None = None


def _load_cases_index() -> dict[str, dict]:
    """Load all tax cases for citation → title lookup."""
    global _CASES_INDEX
    if _CASES_INDEX is not None:
        return _CASES_INDEX
    _CASES_INDEX = {}
    for court in ("hca", "fca", "fcafc", "aata"):
        path = BASE / "data" / f"{court}_tax_cases.json"
        if path.exists():
            with open(path) as f:
                cases = json.load(f)
            for c in cases:
                key = c.get("citation", "").strip()
                _CASES_INDEX[key] = c
    return _CASES_INDEX


def _raw_text_filename(citation: str) -> str:
    """Convert [2015] HCA 48 -> 2015_HCA_48.html"""
    m = _re.match(r"\[(\d+)\]\s*(\S+)\s*(\d+)", citation)
    if m:
        return f"{m.group(1)}_{m.group(2)}_{m.group(3)}.html"
    # fallback: just sanitise
    import re
    return re.sub(r"[\[\]\s/]+", "_", citation) + ".html"


# ── resolve functions ────────────────────────────────────────────────────────


def _has_similarity_index(conn: sqlite3.Connection) -> bool:
    """Check if similarity_index table exists."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='similarity_index'"
    ).fetchone()
    return row is not None


def _add_similarity_edges(conn: sqlite3.Connection, embedding_id: int,
                          node_id: str, nodes: dict, edges: list,
                          max_nodes: int = 20):
    """Add similarity-based edges from the k-NN index. Falls back silently if index missing."""
    if not _has_similarity_index(conn):
        return
    sim_rows = conn.execute(
        "SELECT si.neighbor_id, si.similarity, e.source_type, e.act, e.section, e.section_title "
        "FROM similarity_index si "
        "JOIN embeddings e ON e.id = si.neighbor_id "
        "WHERE si.embedding_id = ? "
        "ORDER BY si.similarity DESC "
        "LIMIT ?",
        (embedding_id, max_nodes),
    ).fetchall()
    for sr in sim_rows:
        stype = sr["source_type"]
        sact = sr["act"]
        ssec = sr["section"]
        stitle = sr["section_title"] or ""
        sim = sr["similarity"]

        if stype == "section":
            tid = f"section:{sact}:{ssec}"
            if tid not in nodes:
                nodes[tid] = {
                    "id": tid,
                    "label": f"{sact}/{ssec} — {stitle}" if stitle else f"{sact}/{ssec}",
                    "short_label": ssec,
                    "group": "section",
                    "url": _section_url(sact, ssec),
                }
        elif stype == "ruling":
            tid = f"ruling:{ssec}"
            if tid not in nodes:
                nodes[tid] = {
                    "id": tid,
                    "label": f"{ssec} — {stitle}" if stitle else ssec,
                    "short_label": ssec,
                    "group": "ruling",
                    "url": _ruling_url(ssec),
                }
        elif stype == "case":
            tid = f"case:{ssec}"
            if tid not in nodes:
                nodes[tid] = {
                    "id": tid,
                    "label": f"{ssec} — {stitle}" if stitle else ssec,
                    "short_label": ssec,
                    "group": "case",
                    "url": _case_url(ssec),
                }
        elif stype == "commentary":
            tid = f"commentary:{sact}:{ssec}"
            if tid not in nodes:
                nodes[tid] = {
                    "id": tid,
                    "label": f"{sact} ¶{ssec} — {stitle}" if stitle else f"{sact} ¶{ssec}",
                    "short_label": f"¶{ssec}",
                    "group": "commentary",
                    "url": "",
                }
        else:
            continue

        edges.append({
            "source": node_id,
            "target": tid,
            "label": f"{sim:.0%}",
            "weight": sim,
            "type": "similarity",
        })
    return


def _resolve_section(act: str, section: str) -> dict:
    """Query cross_references for a section via its embedding_id."""
    conn = sqlite3.connect(str(EMBEDDINGS_DB))
    conn.row_factory = sqlite3.Row
    try:
        # Find embedding_ids for this section
        rows = conn.execute(
            "SELECT id, section_title FROM embeddings "
            "WHERE source_type='section' AND act=? AND section=?",
            (act, section),
        ).fetchall()

        if not rows:
            return {"nodes": [], "edges": []}

        embedding_ids = [r["id"] for r in rows]
        section_title = rows[0]["section_title"] or section
        node_id = f"section:{act}:{section}"

        nodes: dict[str, dict] = {
            node_id: {
                "id": node_id,
                "label": f"{act}/{section} — {section_title}",
                "short_label": section,
                "group": "section",
                "url": _section_url(act, section),
            }
        }
        edges = []

        # Fetch all cross-references for these embedding_ids
        placeholders = ",".join("?" for _ in embedding_ids)
        try:
            refs = conn.execute(
                f"SELECT ref_type, ref_text, ref_target FROM cross_references "
                f"WHERE embedding_id IN ({placeholders})",
                embedding_ids,
            ).fetchall()
        except sqlite3.OperationalError:
            # cross_references table may not exist (new embedding pipeline)
            refs = []

        for ref in refs:
            ref_type = ref["ref_type"]
            target = ref["ref_target"]
            rel = ref["ref_text"] or ""

            if ref_type == "smartlink":
                # target is like "itaa-1997#1-2" or a case citation
                if "#" in target:
                    tgt_act, tgt_sec = target.split("#", 1)
                    tgt_id = f"section:{tgt_act}:{tgt_sec}"
                    if tgt_id not in nodes:
                        trow = conn.execute(
                            "SELECT section_title FROM embeddings "
                            "WHERE source_type='section' AND act=? AND section=? LIMIT 1",
                            (tgt_act, tgt_sec),
                        ).fetchone()
                        label = f"{tgt_act}/{tgt_sec}"
                        if trow and trow["section_title"]:
                            label += f" — {trow['section_title']}"
                        nodes[tgt_id] = {
                            "id": tgt_id,
                            "label": label,
                            "short_label": tgt_sec,
                            "group": "section",
                            "url": _section_url(tgt_act, tgt_sec),
                        }
                    edges.append({
                        "source": node_id,
                        "target": tgt_id,
                        "label": rel,
                    })
                elif target.startswith("["):
                    # Bracket citation = case
                    cid = f"case:{target}"
                    if cid not in nodes:
                        case_idx = _load_cases_index()
                        info = case_idx.get(target, {})
                        label = info.get("title") or target
                        nodes[cid] = {
                            "id": cid,
                            "label": f"{target} — {label}",
                            "short_label": target,
                            "group": "case",
                            "url": _case_url(target),
                        }
                    edges.append({
                        "source": node_id,
                        "target": cid,
                        "label": rel,
                    })
                else:
                    # No bracket = ruling citation
                    rid = f"ruling:{target}"
                    if rid not in nodes:
                        rulings_idx = _load_rulings_index()
                        rkey = target.replace("_", "").replace(" ", "").upper()
                        info = rulings_idx.get(rkey, {}) or None
                        dsp = info.get("display_name") or info.get("citation") or target if info else target
                        rtitle = info.get("full_title") or info.get("title") or "" if info else ""
                        label = f"{dsp} — {rtitle}" if rtitle else dsp
                        nodes[rid] = {
                            "id": rid,
                            "label": label,
                            "short_label": dsp if len(str(dsp)) < 30 else str(dsp)[:30] + "…",
                            "group": "ruling" if info else "case",
                            "url": _ruling_url(dsp) if info else None,
                        }
                    edges.append({
                        "source": node_id,
                        "target": rid,
                        "label": rel,
                    })

            elif ref_type == "defined_term":
                did = f"definition:{target}"
                if did not in nodes:
                    nodes[did] = {
                        "id": did,
                        "label": f"Definition: {target}",
                        "short_label": target,
                        "group": "definition",
                        "url": None,
                    }
                edges.append({
                    "source": node_id,
                    "target": did,
                    "label": rel or "defined",
                })

            elif ref_type == "case":
                cid = f"case:{target}"
                if cid not in nodes:
                    case_idx = _load_cases_index()
                    info = case_idx.get(target, {})
                    label = info.get("title") or target
                    nodes[cid] = {
                        "id": cid,
                        "label": f"{target} — {label}",
                        "short_label": target,
                        "group": "case",
                        "url": _case_url(target),
                    }
                edges.append({
                    "source": node_id,
                    "target": cid,
                    "label": rel or "cited by",
                })

            elif ref_type == "commentary":
                com_id = f"commentary:{target}"
                if com_id not in nodes:
                    nodes[com_id] = {
                        "id": com_id,
                        "label": f"Commentary: {target}",
                        "short_label": target,
                        "group": "commentary",
                        "url": None,
                    }
                edges.append({
                    "source": node_id,
                    "target": com_id,
                    "label": rel or "commentary",
                })

        # Also look up rulings that reference this section
        rulings = _load_rulings_index()
        for cit, info in rulings.items():
            refs_list = info.get("section_refs", []) or info.get("referenced_sections", [])
            if isinstance(refs_list, list):
                for sr in refs_list:
                    if isinstance(sr, dict) and sr.get("section") == section and sr.get("act") == act:
                        rid = f"ruling:{cit}"
                        if rid not in nodes:
                            display = info.get("display_name") or info.get("citation") or cit
                            title = info.get("full_title") or info.get("title") or ""
                            label = f"{display} — {title}" if title else display
                            nodes[rid] = {
                                "id": rid,
                                "label": label,
                                "short_label": display if len(str(display)) < 30 else str(display)[:30] + "…",
                                "group": "ruling",
                                "url": _ruling_url(cit),
                            }
                        edges.append({
                            "source": node_id,
                            "target": rid,
                            "label": "ruling",
                        })
                        break

        # Also look up cases that reference this section from section_case_index.json
        global _SECTION_CASE_INDEX
        if _SECTION_CASE_INDEX is None:
            sc_path = BASE / "data" / "section_case_index.json"
            if sc_path.exists():
                with open(sc_path) as f:
                    _SECTION_CASE_INDEX = json.load(f)
            else:
                _SECTION_CASE_INDEX = {}
        case_refs = _SECTION_CASE_INDEX.get(f"{act}:{section}", [])
        case_idx = _load_cases_index()
        for cr in case_refs[:30]:  # cap at 30 cases to avoid overwhelming the graph
            cit = cr.get("citation", "")
            if not cit:
                continue
            cid = f"case:{cit}"
            if cid not in nodes:
                info = case_idx.get(cit, {})
                label = info.get("title") or cit
                nodes[cid] = {
                    "id": cid,
                    "label": f"{cit} — {label}",
                    "short_label": cit,
                    "group": "case",
                    "url": _case_url(cit),
                }
            edges.append({
                "source": node_id,
                "target": cid,
                "label": "section",
            })

        # Add similarity-based edges from k-NN index
        for emb_id in embedding_ids:
            _add_similarity_edges(conn, emb_id, node_id, nodes, edges)

        return {"nodes": list(nodes.values()), "edges": edges}
    finally:
        conn.close()


def _resolve_ruling(citation: str) -> dict:
    """Build graph for a ruling by finding referenced sections & cases."""
    # Normalise citation — strip spaces, underscores, slashes for index lookup
    def _norm(s):
        return s.replace(" ", "").replace("_", "").replace("/", "").upper()

    norm_slashed = citation.replace("_", " ").upper().strip()
    norm_key = _norm(norm_slashed)
    rulings = _load_rulings_index()
    info = rulings.get(norm_key)
    if not info:
        # Try matching
        for k, v in rulings.items():
            if norm_key in k or norm_key == _norm(k):
                info = v
                break
    if not info:
        return {"nodes": [], "edges": [], "error": f"Ruling not found: {citation}"}

    display = info.get("display_name") or info.get("citation") or citation
    rid = f"ruling:{display}"
    nodes = {
        rid: {
            "id": rid,
            "label": f"{display} — {info.get('full_title') or info.get('title') or ''}",
            "short_label": display,
            "group": "ruling",
            "url": _ruling_url(display),
        }
    }
    edges = []

    conn = sqlite3.connect(str(EMBEDDINGS_DB))
    conn.row_factory = sqlite3.Row
    try:
        refs_list = info.get("section_refs", []) or info.get("referenced_sections", [])
        if isinstance(refs_list, list):
            for sr in refs_list:
                if isinstance(sr, dict):
                    act = sr.get("act", "")
                    sec = sr.get("section", "")
                    if act and sec:
                        sid = f"section:{act}:{sec}"
                        if sid not in nodes:
                            trow = conn.execute(
                                "SELECT section_title FROM embeddings "
                                "WHERE source_type='section' AND act=? AND section=? LIMIT 1",
                                (act, sec),
                            ).fetchone()
                            label = f"{act}/{sec}"
                            if trow and trow["section_title"]:
                                label += f" — {trow['section_title']}"
                            nodes[sid] = {
                                "id": sid,
                                "label": label,
                                "short_label": sec,
                                "group": "section",
                                "url": _section_url(act, sec),
                            }
                        edges.append({"source": rid, "target": sid, "label": "references"})

        # Cases citing this ruling (from case section_refs)
        cases = _load_cases_index()
        for cit, c in cases.items():
            refs = c.get("section_refs", [])
            if isinstance(refs, list):
                for r in refs:
                    if isinstance(r, dict) and r.get("section", "").replace("_", " ").upper() == norm_slashed.replace(" ", ""):
                        cid = f"case:{cit}"
                        if cid not in nodes:
                            label = c.get("title") or cit
                            nodes[cid] = {
                                "id": cid,
                                "label": f"{cit} — {label}",
                                "short_label": cit,
                                "group": "case",
                                "url": _case_url(cit),
                            }
                        edges.append({"source": rid, "target": cid, "label": "cited by"})
                        break

        # Add similarity edges from k-NN index
        # Normalise display to match embedding DB format (underscores → spaces/slashes)
        # Pattern: TR_2025_1 → TR 2025/1
        db_section = _re.sub(r"^(\w+)_(\d+)_(\d+)$", r"\1 \2/\3", display)
        emb_row = conn.execute(
            "SELECT id FROM embeddings WHERE source_type='ruling' AND section=? LIMIT 1",
            (db_section,),
        ).fetchone()
        if emb_row:
            _add_similarity_edges(conn, emb_row["id"], rid, nodes, edges)
    finally:
        conn.close()

    return {"nodes": list(nodes.values()), "edges": edges}


def _resolve_case(citation: str) -> dict:
    """Build graph for a case by finding referenced sections, rulings & cases."""
    norm = citation.strip()
    # Get case metadata from the index
    cases = _load_cases_index()
    case_info = cases.get(norm)
    if not case_info:
        return {"nodes": [], "edges": [], "error": f"Case not found: {citation}"}

    title = case_info.get("title") or ""
    cid = f"case:{norm}"
    nodes = {
        cid: {
            "id": cid,
            "label": f"{norm} — {title}",
            "short_label": norm,
            "group": "case",
            "url": _case_url(norm),
        }
    }
    edges = []

    conn = sqlite3.connect(str(EMBEDDINGS_DB))
    conn.row_factory = sqlite3.Row
    try:
        # Sections referenced by this case
        refs = case_info.get("section_refs", [])
        if isinstance(refs, list):
            for r in refs:
                if isinstance(r, dict):
                    act = r.get("act", "")
                    sec = r.get("section", "")
                    if act and sec:
                        sid = f"section:{act}:{sec}"
                        if sid not in nodes:
                            trow = conn.execute(
                                "SELECT section_title FROM embeddings "
                                "WHERE source_type='section' AND act=? AND section=? LIMIT 1",
                                (act, sec),
                            ).fetchone()
                            label = f"{act}/{sec}"
                            if trow and trow["section_title"]:
                                label += f" — {trow['section_title']}"
                            nodes[sid] = {
                                "id": sid,
                                "label": label,
                                "short_label": sec,
                                "group": "section",
                                "url": _section_url(act, sec),
                            }
                        edges.append({"source": cid, "target": sid, "label": "references"})

        # Rulings mentioning this case (check ruling section_refs for case citation)
        rulings = _load_rulings_index()
        for rc, rinfo in rulings.items():
            rrefs = rinfo.get("section_refs", []) or rinfo.get("referenced_sections", [])
            if isinstance(rrefs, list):
                for rr in rrefs:
                    if isinstance(rr, dict) and rr.get("section", "").strip() == norm.replace(" ", ""):
                        rid = f"ruling:{rc}"
                        if rid not in nodes:
                            dsp = rinfo.get("display_name") or rinfo.get("citation") or rc
                            rtitle = rinfo.get("full_title") or rinfo.get("title") or ""
                            label = f"{dsp} — {rtitle}" if rtitle else dsp
                            nodes[rid] = {
                                "id": rid,
                                "label": label,
                                "short_label": dsp if len(str(dsp)) < 30 else str(dsp)[:30] + "…",
                                "group": "ruling",
                                "url": _ruling_url(dsp),
                            }
                        edges.append({"source": cid, "target": rid, "label": "referenced by"})
                        break

        # Add similarity edges from k-NN index
        emb_row = conn.execute(
            "SELECT id FROM embeddings WHERE source_type='case' AND section=? LIMIT 1",
            (norm,),
        ).fetchone()
        if emb_row:
            _add_similarity_edges(conn, emb_row["id"], cid, nodes, edges)
    finally:
        conn.close()

    return {"nodes": list(nodes.values()), "edges": edges}


# ── API endpoint ─────────────────────────────────────────────────────────────


@router.get("/api/graph/data")
def graph_data(
    type: str = Query(alias="type"),
    act: str | None = Query(default=None),
    section: str | None = Query(default=None),
    citation: str | None = Query(default=None),
    depth: int = Query(default=1, ge=1, le=3),
):
    """Return nodes and edges for a force-directed graph centered on an item.

    Query params:
      type:      "section", "ruling", or "case"
      act:       act key (required for type=section), e.g. "itaa-1997"
      section:   section id (required for type=section), e.g. "8-1"
      citation:  citation (required for type=ruling or case), e.g. "TR 2025/1"
      depth:     expansion depth (1-3, default 1). Higher = more neighbours.
    """
    if type == "section":
        if not act or not section:
            return JSONResponse({"error": "act and section required for type=section"}, status_code=400)
        result = _resolve_section(act, section)
    elif type == "ruling":
        if not citation:
            return JSONResponse({"error": "citation required for type=ruling"}, status_code=400)
        result = _resolve_ruling(citation)
    elif type == "case":
        if not citation:
            return JSONResponse({"error": "citation required for type=case"}, status_code=400)
        result = _resolve_case(citation)
    else:
        return JSONResponse({"error": f"Unknown type: {type}"}, status_code=400)

    result["meta"] = {"type": type, "depth": depth, "node_count": len(result["nodes"]), "edge_count": len(result["edges"])}
    return result