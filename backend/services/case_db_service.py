"""Service layer for case-related database queries.

Reuses _sql() / _sql_dict() from tax_case_sql.py to query the
Cadena Knowledge Postgres database via docker exec.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from backend.services.tax_case_sql import _sql, _sql_dict

logger = logging.getLogger(__name__)

# Citation regex: [YEAR] COURT NUMBER
_CITATION_RE = re.compile(r"\[(\d+)\]\s+(\w+)\s+(\d+)")


# ---------------------------------------------------------------------------
# Helper: parse citation into components
# ---------------------------------------------------------------------------


def _parse_citation(citation: str) -> dict[str, str | int] | None:
    """Parse ``[2024] HCA 1`` → ``{year: 2024, court: 'HCA', num: 1}``."""
    m = _CITATION_RE.match(citation.strip())
    if not m:
        return None
    return {"year": int(m.group(1)), "court": m.group(2), "num": int(m.group(3))}


def _safe(val: str) -> str:
    """Escape single quotes for SQL."""
    return val.replace("'", "''")


# ---------------------------------------------------------------------------
# Tool 1: get_case_metadata
# ---------------------------------------------------------------------------


def get_case_metadata(
    citation: str,
    include_legislation_refs: bool = False,
) -> dict[str, Any] | None:
    """Return case metadata + structural outline (no paragraph text).

    Args:
        citation: e.g. ``[2024] HCA 1``.
        include_legislation_refs: If True also return legislation references.

    Returns:
        Dict with case info, or None if not found.
    """
    safe = _safe(citation)

    # ── case row ──────────────────────────────────────────────────────────
    rows = _sql_dict(
        [
            "id",
            "citation",
            "case_name",
            "court",
            "decision_date",
            "judges",
            "outcome",
            "related_provisions",
            "related_rulings",
            "head_notes",
        ],
        f"SELECT id, citation, case_name, court, decision_date::text, judges, "
        f"outcome, related_provisions, related_rulings, head_notes::text "
        f"FROM cases WHERE citation = '{safe}' LIMIT 1",
    )
    if not rows:
        return None

    case = rows[0]
    case_id = case["id"]

    # Clean array fields
    for arr_field in ("judges", "related_provisions", "related_rulings"):
        if isinstance(case.get(arr_field), list):
            case[arr_field] = [str(s).strip('"') for s in case[arr_field]]
        elif case.get(arr_field) is None:
            case[arr_field] = []

    # Parse head_notes JSON
    if isinstance(case.get("head_notes"), str):
        try:
            import json

            case["head_notes"] = json.loads(case["head_notes"])
        except Exception:
            pass

    # ── content_length from documents ─────────────────────────────────────
    doc_rows = _sql_dict(
        ["content_length"],
        f"SELECT LENGTH(content) as content_length FROM documents "
        f"WHERE id = (SELECT document_id FROM cases WHERE citation = '{safe}')",
    )
    content_length = doc_rows[0]["content_length"] if doc_rows else None

    # ── cited_by_count ────────────────────────────────────────────────────
    cite_rows = _sql_dict(
        ["cnt"],
        f"SELECT COUNT(*) as cnt FROM case_citations "
        f"WHERE cited_citation = '{safe}'",
    )
    cited_by_count = cite_rows[0]["cnt"] if cite_rows else 0

    # ── legislation_refs_count ────────────────────────────────────────────
    leg_rows = _sql_dict(
        ["cnt"],
        f"SELECT COUNT(*) as cnt FROM case_legislation_refs "
        f"WHERE case_id = '{case_id}'",
    )
    legislation_refs_count = leg_rows[0]["cnt"] if leg_rows else 0

    # ── paragraph count ───────────────────────────────────────────────────
    para_rows = _sql_dict(
        ["cnt"],
        f"SELECT COUNT(*) as cnt FROM case_paragraphs "
        f"WHERE case_id = '{case_id}'",
    )
    paragraph_count = para_rows[0]["cnt"] if para_rows else 0

    # ── section outline ───────────────────────────────────────────────────
    outline_rows = _sql_dict(
        ["section_type", "count", "start_seq", "end_seq"],
        f"SELECT section_type, COUNT(*) as count, "
        f"MIN(sequence_order) as start_seq, MAX(sequence_order) as end_seq "
        f"FROM case_paragraphs "
        f"WHERE case_id = '{case_id}' "
        f"GROUP BY section_type ORDER BY MIN(sequence_order)",
    )

    # ── download URLs ─────────────────────────────────────────────────────
    parsed = _parse_citation(citation)
    download_urls = {}
    if parsed:
        court = str(parsed["court"])
        year = str(parsed["year"])
        num = str(parsed["num"])
        download_urls["austlii_url"] = (
            f"https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/"
            f"cth/{court}/{year}/{num}.html"
        )

    # ── assemble result ───────────────────────────────────────────────────
    result: dict[str, Any] = {
        "citation": case.get("citation"),
        "case_name": case.get("case_name"),
        "court": case.get("court"),
        "decision_date": case.get("decision_date"),
        "judges": case.get("judges"),
        "outcome": case.get("outcome"),
        "head_notes": case.get("head_notes"),
        "related_provisions": case.get("related_provisions"),
        "related_rulings": case.get("related_rulings"),
        "content_length": content_length,
        "paragraph_count": paragraph_count,
        "cited_by_count": cited_by_count,
        "legislation_refs_count": legislation_refs_count,
        "section_outline": outline_rows,
        "download_urls": download_urls,
    }

    # ── optional legislation refs ─────────────────────────────────────────
    if include_legislation_refs:
        leg_rows = _sql_dict(
            ["act_title", "section_reference", "context", "paragraph_number"],
            f"SELECT act_title, section_reference, context, paragraph_number "
            f"FROM case_legislation_refs "
            f"WHERE case_id = '{case_id}' ORDER BY paragraph_number",
        )
        result["legislation_refs"] = leg_rows

    return result


# ---------------------------------------------------------------------------
# Tool 2: get_case_paragraphs
# ---------------------------------------------------------------------------


def get_case_paragraphs(
    citation: str,
    section_types: list[str] | None = None,
    paragraph_start: int = 0,
    paragraph_limit: int = 50,
    range_start: int | None = None,
    range_end: int | None = None,
) -> dict[str, Any]:
    """Return paragraphs from a case, filtered and paginated.

    At least one of *section_types* or *range_start* must be provided.
    Hard caps: 100 paragraphs max, 50 000 characters total content.
    """
    safe = _safe(citation)

    # ── validate at least one filter ──────────────────────────────────────
    if not section_types and range_start is None and range_end is None:
        return {
            "error": (
                "At least one filter is required: section_types, "
                "range_start, or range_end. Use get_case first to see "
                "available section types and sequence ranges."
            ),
        }

    paragraph_limit = min(100, max(1, paragraph_limit))

    # ── WHERE clauses ─────────────────────────────────────────────────────
    wheres = [
        f"cp.case_id = (SELECT id FROM cases WHERE citation = '{safe}')"
    ]

    if section_types:
        # Build an IN clause with escaped values
        escaped = [f"'{_safe(t)}'" for t in section_types if t]
        if escaped:
            wheres.append(f"cp.section_type IN ({','.join(escaped)})")

    if range_start is not None:
        wheres.append(f"cp.sequence_order >= {int(range_start)}")
    if range_end is not None:
        wheres.append(f"cp.sequence_order <= {int(range_end)}")

    where_clause = " AND ".join(wheres)

    # ── total_matching count ──────────────────────────────────────────────
    count_rows = _sql_dict(
        ["cnt"],
        f"SELECT COUNT(*) as cnt FROM case_paragraphs cp WHERE {where_clause}",
    )
    total_matching = count_rows[0]["cnt"] if count_rows else 0

    # ── total_in_case count ───────────────────────────────────────────────
    case_count_rows = _sql_dict(
        ["cnt"],
        f"SELECT COUNT(*) as cnt FROM case_paragraphs cp "
        f"WHERE cp.case_id = (SELECT id FROM cases WHERE citation = '{safe}')",
    )
    total_in_case = case_count_rows[0]["cnt"] if case_count_rows else 0

    # ── fetch paragraphs ──────────────────────────────────────────────────
    rows = _sql_dict(
        [
            "paragraph_number",
            "paragraph_label",
            "section_type",
            "content",
            "sequence_order",
        ],
        f"SELECT cp.paragraph_number, cp.paragraph_label, cp.section_type, "
        f"REPLACE(cp.content, '|', ' ') as content, cp.sequence_order "
        f"FROM case_paragraphs cp "
        f"WHERE {where_clause} "
        f"ORDER BY cp.sequence_order NULLS LAST, cp.paragraph_number "
        f"OFFSET {int(paragraph_start)} LIMIT {paragraph_limit}",
    )

    # ── content character cap (50K) ───────────────────────────────────────
    total_chars = 0
    truncated = False
    capped_rows: list[dict[str, Any]] = []
    for r in rows:
        content = r.get("content") or ""
        content_len = len(content)
        if total_chars + content_len > 50000:
            truncated = True
            break
        capped_rows.append(r)
        total_chars += content_len

    return {
        "citation": citation,
        "total_matching": total_matching,
        "total_in_case": total_in_case,
        "returned_count": len(capped_rows),
        "truncated": truncated,
        "paragraphs": capped_rows,
    }


# ---------------------------------------------------------------------------
# Tool 3: search_case_paragraphs
# ---------------------------------------------------------------------------


def search_case_paragraphs(
    query: str,
    citation: str | None = None,
    section_types: list[str] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Full-text search across case paragraphs using ILIKE.

    If *citation* is provided, search is scoped to that one case.
    If None, searches all cases (cross-case).

    Args:
        query: The search string.
        citation: Optional case citation to scope the search.
        section_types: Optional list of section types to filter.
        limit: Max results. 100 max for within-case, 30 max for cross-case.

    Returns:
        Dict with query, citation_filter, total_matches, results.
    """
    safe_query = _safe(query)

    # ── enforce per-mode limits ───────────────────────────────────────────
    if citation:
        limit = min(100, max(1, limit))
    else:
        limit = min(30, max(1, limit))

    # ── build WHERE clauses ───────────────────────────────────────────────
    wheres = [f"cp.content ILIKE '%{safe_query}%'"]

    if citation:
        safe_cite = _safe(citation)
        wheres.append(f"c.citation = '{safe_cite}'")

    if section_types:
        escaped = [f"'{_safe(t)}'" for t in section_types if t]
        if escaped:
            wheres.append(f"cp.section_type IN ({','.join(escaped)})")

    where_clause = " AND ".join(wheres)

    # ── count total matches ───────────────────────────────────────────────
    count_rows = _sql_dict(
        ["cnt"],
        f"SELECT COUNT(*) as cnt "
        f"FROM case_paragraphs cp "
        f"JOIN cases c ON c.id = cp.case_id "
        f"WHERE {where_clause}",
    )
    total_matches = count_rows[0]["cnt"] if count_rows else 0

    # ── fetch results ─────────────────────────────────────────────────────
    rows = _sql_dict(
        [
            "citation",
            "case_name",
            "court",
            "section_type",
            "paragraph_number",
            "snippet",
            "content_length",
            "sequence_order",
        ],
        f"SELECT c.citation, c.case_name, c.court, "
        f"cp.section_type, cp.paragraph_number, "
        f"REPLACE(LEFT(cp.content, 300), '|', ' ') as snippet, "
        f"LENGTH(cp.content) as content_length, "
        f"cp.sequence_order "
        f"FROM case_paragraphs cp "
        f"JOIN cases c ON c.id = cp.case_id "
        f"WHERE {where_clause} "
        f"ORDER BY c.citation, cp.sequence_order "
        f"LIMIT {limit}",
    )

    return {
        "query": query,
        "citation_filter": citation,
        "total_matches": total_matches,
        "results": rows,
    }


# ---------------------------------------------------------------------------
# Tool 4: build_download_urls
# ---------------------------------------------------------------------------


def build_download_urls(citation: str) -> dict[str, Any] | None:
    """Return download links for a case, plus case name.

    URLs are generated from the citation pattern. Does NOT hit the
    database for anything but case_name retrieval.

    Returns:
        Dict with citation, case_name, austlii_url, note; or None if
        the citation cannot be parsed or case not found.
    """
    parsed = _parse_citation(citation)
    if not parsed:
        return None

    court = str(parsed["court"])
    year = str(parsed["year"])
    num = str(parsed["num"])

    # Build AustLII URL
    austlii_url = (
        f"https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/"
        f"cth/{court}/{year}/{num}.html"
    )

    # Fetch case_name from DB so we can include it
    safe = _safe(citation)
    name_rows = _sql_dict(
        ["case_name", "court", "decision_date"],
        f"SELECT case_name, court, decision_date::text "
        f"FROM cases WHERE citation = '{safe}' LIMIT 1",
    )
    case_name = name_rows[0].get("case_name") if name_rows else None

    # Fetch paragraph count too
    para_count = 0
    if name_rows:
        case_id_rows = _sql_dict(
            ["id"],
            f"SELECT id FROM cases WHERE citation = '{safe}' LIMIT 1",
        )
        if case_id_rows:
            cid = case_id_rows[0]["id"]
            cnt_rows = _sql_dict(
                ["cnt"],
                f"SELECT COUNT(*) as cnt FROM case_paragraphs "
                f"WHERE case_id = '{cid}'",
            )
            para_count = cnt_rows[0]["cnt"] if cnt_rows else 0

    return {
        "citation": citation,
        "case_name": case_name,
        "austlii_url": austlii_url,
        "content_length": None,  # not fetched here; use get_case_metadata
        "paragraph_count": para_count,
        "note": (
            "Full text is available for download from AustLII or court "
            "website. MCP does not serve full text to avoid context "
            "overflow. Use get_case_paragraphs for structured access. "
            "If downloading via curl/HTTP fails (e.g. bot protection on "
            "AustLII), ask the user to open the URL in a regular browser "
            "to download the case manually."
        ),
    }
