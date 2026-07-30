"""Service layer for case-related database queries.

Reuses _sql() / _sql_dict() from tax_case_sql.py to query the
Cadena Knowledge Postgres database via docker exec.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from backend.services.tax_case_sql import _sql, _sql_dict
from backend.services.text_cleaner import clean_case_paragraph

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

    # Clean AustLII navigation garbage from key_terms
    _AUSTLII_NAV = {
        "databases", "noteup", "name search", "database search",
        "last updated", "notice", "commonwealth law reports",
        "austlii", "austlii home", "austlii database", "citation",
        "print", "download", "email", "full text", "help",
        "cookie", "privacy", "disclaimer", "copyright",
    }
    if isinstance(case.get("head_notes"), dict):
        key_terms = case["head_notes"].get("key_terms", [])
        if isinstance(key_terms, list):
            cleaned = [
                t for t in key_terms
                if isinstance(t, str) and t.strip().lower() not in _AUSTLII_NAV
            ]
            case["head_notes"]["key_terms"] = cleaned

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
        "decision_date_note": None,
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

    # Flag year-only dates (e.g. "2016-01-01" when the real date is 2016-11-16)
    dd = case.get("decision_date")
    if dd and isinstance(dd, str) and dd.endswith("-01-01"):
        result["decision_date_note"] = "Year only — exact date unknown (defaulted to Jan 1)"

    # ── optional legislation refs ─────────────────────────────────────────
    if include_legislation_refs:
        leg_rows = _sql_dict(
            ["act_title", "section_reference", "context", "paragraph_number"],
            f"SELECT act_title, section_reference, context, paragraph_number "
            f"FROM case_legislation_refs "
            f"WHERE case_id = '{case_id}' ORDER BY paragraph_number",
        )
        # Post-process: fix known ITAA 1936 sections mislabelled as ITAA 1997
        # These are simple-integer sections from ITAA 1936 Part III Div 6, 7, 7A, etc.
        # that the ingestion logic defaulted to 1997.
        _ITAA1936_SECTIONS = {
            "s.95", "s.96", "s.97", "s.97(1)", "s.98", "s.99", "s.100", "s.100A",
            "s.101", "s.102", "s.102A", "s.103", "s.103A", "s.104",
            "s.105", "s.106", "s.107", "s.108", "s.109", "s.109A",
            "s.109B", "s.109C", "s.109D", "s.109E", "s.109F", "s.109G",
            "s.109H", "s.109J", "s.109K", "s.109L", "s.109M", "s.109N",
            "s.109P", "s.109Q", "s.109R", "s.109S", "s.109T", "s.109U",
            "s.109V", "s.109W", "s.109X", "s.109Y", "s.109Z", "s.109ZA", "s.109ZB",
            "s.110", "s.111", "s.112", "s.113", "s.114", "s.115", "s.116",
            "s.117", "s.118", "s.119", "s.120", "s.121", "s.122", "s.123",
            "s.124", "s.125", "s.126", "s.127", "s.128",
            "s.160ZA", "s.160ZB", "s.160ZC", "s.160ZD",
            "s.177A", "s.177B", "s.177C", "s.177D", "s.177E", "s.177F", "s.177G",
            "s.200", "s.201", "s.202", "s.202A",
            "s.221A", "s.221B", "s.221C", "s.221D",
            "s.221H", "s.221J", "s.221K", "s.221L",
            "s.221P", "s.221Q", "s.221R", "s.221S", "s.221T",
            "s.221Y", "s.221YA", "s.221YB", "s.221YC", "s.221YD",
            "s.221YH", "s.221YHJ", "s.221YHK", "s.221YHL", "s.221YHM",
            "s.254", "s.255", "s.256", "s.257", "s.258",
            "s.255-1",  # TAA 1953
        }
        for row in leg_rows:
            ref = (row.get("section_reference") or "").lower().strip()
            at = row.get("act_title") or ""
            if "1997" in at and ref in _ITAA1936_SECTIONS:
                row["act_title"] = "Income Tax Assessment Act 1936"
                row["_act_corrected"] = True
            # Also handle subsection variants like s.97(1) by stripping the subsection
            if "1997" in at and not row.get("_act_corrected"):
                base_ref = re.sub(r'\(.*\)', '', ref).strip()
                if base_ref in _ITAA1936_SECTIONS:
                    row["act_title"] = "Income Tax Assessment Act 1936"
                    row["_act_corrected"] = True
        result["legislation_refs"] = leg_rows

    return result


def get_case_references(citation: str) -> dict[str, Any]:
    """Return legislation references and case citations for a case.

    Queries both ``case_legislation_refs`` and ``case_citations`` tables.

    Args:
        citation: e.g. ``[2024] HCA 1``.

    Returns:
        Dict with legislation_refs and case_citations arrays.
    """
    safe = _safe(citation)

    # Get case_id
    id_rows = _sql_dict(
        ["id"],
        f"SELECT id FROM cases WHERE citation = '{safe}' LIMIT 1",
    )
    if not id_rows:
        return {"legislation_refs": [], "case_citations": [], "note": "Case not found"}

    case_id = id_rows[0]["id"]
    cid_str = str(case_id)

    # Legislation refs
    leg_rows = _sql_dict(
        ["act_title", "section_reference", "context", "paragraph_number"],
        f"SELECT act_title, section_reference, context, paragraph_number "
        f"FROM case_legislation_refs "
        f"WHERE case_id = '{cid_str}' ORDER BY paragraph_number",
    )

    # Case citations (cases this case cites)
    cite_rows = _sql_dict(
        ["cited_citation", "cited_case_name", "context", "paragraph_number"],
        f"SELECT cited_citation, cited_case_name, context, paragraph_number "
        f"FROM case_citations "
        f"WHERE citing_case_id = '{cid_str}' ORDER BY paragraph_number",
    )

    # Cases that cite this case
    cited_by_rows = _sql_dict(
        ["citation", "case_name"],
        f"SELECT c.citation, c.case_name FROM case_citations cc "
        f"JOIN cases c ON c.id = cc.citing_case_id "
        f"WHERE cc.cited_citation = '{safe}' "
        f"GROUP BY c.citation, c.case_name ORDER BY c.citation",
    )

    return {
        "legislation_refs": leg_rows,
        "case_citations": cite_rows,
        "cited_by": cited_by_rows,
    }


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

    # ── validate at least one filter ── otherwise default to first paragraphs
    if not section_types and range_start is None and range_end is None:
        # No filter — return first paragraphs (will be caught by the WHERE clause
        # which already scopes by case_id)
        pass

    paragraph_limit = min(200, max(1, paragraph_limit))

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
    total_in_case_before_filter = count_rows[0]["cnt"] if count_rows else 0

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

    # Clean AustLII navigation noise from each paragraph
    filtered_rows = []
    for r in rows:
        content = r.get("content") or ""
        content = clean_case_paragraph(content)
        if not content:
            continue  # skip paragraphs that are pure noise
        r["content"] = content
        filtered_rows.append(r)

    return {
        "citation": citation,
        "total_matching": len(filtered_rows),
        "total_in_case": total_in_case_before_filter,
        "returned_count": len(filtered_rows),
        "truncated": False,
        "warning": (
            "Paragraphs may be segmented mid-sentence. Cross-reference with "
            "the full judgment before citing."
        ),
        "paragraphs": filtered_rows,
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
        f"REPLACE(cp.content, '|', ' ') as content, "
        f"LENGTH(cp.content) as content_length, "
        f"cp.sequence_order "
        f"FROM case_paragraphs cp "
        f"JOIN cases c ON c.id = cp.case_id "
        f"WHERE {where_clause} "
        f"ORDER BY c.citation, cp.sequence_order "
        f"LIMIT {limit}",
    )

    # Build centred snippets
    snippet_results = []
    for row in rows:
        content = row.get("snippet") or ""
        idx = content.lower().find(safe_query.lower())
        if idx >= 0:
            window = 150
            start = max(0, idx - window)
            end = min(len(content), idx + len(safe_query) + window)
            snippet = content[start:end]
            if start > 0:
                snippet = "..." + snippet.lstrip()
            if end < len(content):
                snippet = snippet.rstrip() + "..."
        else:
            snippet = content[:300]
        row["snippet"] = snippet
        snippet_results.append(row)

    return {
        "query": query,
        "citation_filter": citation,
        "total_matches": total_matches,
        "results": snippet_results,
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

    # Build court-specific URL
    court_url = None
    if court == "HCA":
        court_url = f"https://www.hcourt.gov.au/cases/case_{year}_{num}.html"
    elif court in ("FCA", "FCAFC"):
        court_url = (
            f"https://www.judgments.fedcourt.gov.au/judgment/Judgments/"
            f"{court}/{year}/"
        )

    # Fetch case_name from DB so we can include it
    safe = _safe(citation)
    name_rows = _sql_dict(
        ["case_name", "court", "decision_date"],
        f"SELECT case_name, court, decision_date::text "
        f"FROM cases WHERE citation = '{safe}' LIMIT 1",
    )
    case_name = name_rows[0].get("case_name") if name_rows else None

    # Fetch paragraph count + content length
    para_count = 0
    content_length = None
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
            doc_rows = _sql_dict(
                ["content_length"],
                f"SELECT LENGTH(content) as content_length FROM documents "
                f"WHERE id = (SELECT document_id FROM cases WHERE citation = '{safe}')",
            )
            if doc_rows:
                content_length = doc_rows[0]["content_length"]

    return {
        "citation": citation,
        "case_name": case_name,
        "austlii_url": austlii_url,
        "court_url": court_url,
        "content_length": content_length,
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
