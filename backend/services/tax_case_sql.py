"""Query the Cadena Knowledge PostgreSQL database for tax case data.

Uses docker exec to run queries inside the cadena-postgres container.
"""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

_PSQL = [
    "docker", "exec", "cadena-postgres",
    "psql", "-U", "postgres", "-d", "cadena_knowledge",
    "-t", "-F", "|", "-A",  # tuples-only, pipe-sep, unaligned (no headers)
]


def _sql(query: str) -> list[list[str]]:
    """Run a SQL query via docker exec. Returns rows as list of string lists."""
    try:
        result = subprocess.run(
            _PSQL + ["-c", query],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            logger.warning(f"SQL query failed: {result.stderr[:200]}")
            return []
        return _parse_rows(result.stdout)
    except subprocess.TimeoutExpired:
        logger.warning("SQL query timed out")
        return []
    except FileNotFoundError:
        logger.warning("docker not available")
        return []
    except Exception as e:
        logger.exception(f"SQL query error: {e}")
        return []


def _parse_rows(output: str) -> list[list[str]]:
    """Parse psql -t -F '|' -A output into list of string lists."""
    rows = []
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue
        rows.append([cell.strip() for cell in line.split("|")])
    return rows


def _to_dict(columns: list[str], row: list[str]) -> dict[str, Any]:
    """Map a row of values to column names, with type inference."""
    result = {}
    for i, col in enumerate(columns):
        val = row[i] if i < len(row) else None
        if val is None or val == "" or val == "NULL":
            result[col] = None
        else:
            # Try to parse known types
            result[col] = _infer_type(val)
    return result


def _infer_type(val: str) -> Any:
    """Infer the type of a psql string value."""
    # JSON object (must check before PG array literal since both use {})
    if val.startswith("{\"") and val.endswith("}"):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val
    # PostgreSQL array literal: {value1,value2}
    if val.startswith("{") and val.endswith("}"):
        return _parse_pg_array(val)
    # JSON array
    if val.startswith("[") and val.endswith("]"):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val
    # Number
    try:
        if "." in val:
            return float(val)
        return int(val)
    except (ValueError, TypeError):
        pass
    return val


def _parse_pg_array(val: str) -> list[Any]:
    """Parse PostgreSQL array literal like {value1,value2}."""
    inner = val[1:-1]
    if not inner.strip():
        return []
    items = []
    current: list[str] = []
    in_quotes = False
    for ch in inner:
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == "," and not in_quotes:
            items.append("".join(current).strip().strip('"'))
            current = []
        else:
            current.append(ch)
    if current:
        items.append("".join(current).strip().strip('"'))
    return items


def _sql_dict(columns: list[str], query: str) -> list[dict[str, Any]]:
    """Run SQL and return results as list of dicts with given column names."""
    rows = _sql(query)
    return [_to_dict(columns, row) for row in rows]


def get_case_sql_data(citation: str) -> dict[str, Any] | None:
    """Fetch SQL-stored data for a case by citation.

    Returns None if not found or DB unavailable.
    """
    # Escape single quotes for SQL
    safe_citation = citation.replace("'", "''")

    # 1. Find the document
    docs = _sql_dict(
        ["id", "reference", "title", "content_length"],
        f"SELECT id, reference, title, LENGTH(content) FROM documents "
        f"WHERE doc_type='case' AND reference = '{safe_citation}' LIMIT 1",
    )
    if not docs:
        return None

    doc = docs[0]
    doc_id = doc.get("id")
    if not doc_id:
        return None

    # 2. Get content preview
    preview_rows = _sql_dict(
        ["preview"],
        f"SELECT LEFT(content, 2000) FROM documents WHERE id = '{doc_id}'",
    )
    preview = preview_rows[0]["preview"] if preview_rows else ""

    # 3. Get chunk info
    chunks = _sql_dict(
        ["chunk_index", "content_length"],
        f"SELECT chunk_index, LENGTH(content) FROM chunks "
        f"WHERE document_id = '{doc_id}' ORDER BY chunk_index",
    )

    # 4. Get case metadata from cases table
    case_meta_rows = _sql_dict(
        ["citation", "case_name", "court", "decision_date", "judges", "outcome",
         "related_provisions", "related_rulings", "head_notes"],
        f"SELECT citation, case_name, court, decision_date::text, judges, outcome, "
        f"related_provisions, related_rulings, head_notes::text "
        f"FROM cases WHERE document_id = '{doc_id}' LIMIT 1",
    )
    case_meta = case_meta_rows[0] if case_meta_rows else {}

    # Clean up array fields
    for arr_field in ["judges", "related_provisions", "related_rulings"]:
        if isinstance(case_meta.get(arr_field), list):
            case_meta[arr_field] = [str(s).strip('"') for s in case_meta[arr_field]]
        elif case_meta.get(arr_field) is None:
            case_meta[arr_field] = []

    # Parse head_notes JSON
    if isinstance(case_meta.get("head_notes"), str):
        try:
            case_meta["head_notes"] = json.loads(case_meta["head_notes"])
        except (json.JSONDecodeError, TypeError):
            pass

    # 5. Get paragraphs
    paragraphs = _sql_dict(
        ["paragraph_number", "paragraph_label", "section_type", "content_preview", "content_length", "sequence_order"],
        f"SELECT paragraph_number, paragraph_label, section_type, "
        f"LEFT(content, 500), LENGTH(content), sequence_order "
        f"FROM case_paragraphs "
        f"WHERE case_id IN (SELECT id FROM cases WHERE document_id = '{doc_id}') "
        f"ORDER BY sequence_order NULLS LAST, paragraph_number",
    )

    return {
        "slug": doc_id,
        "full_content_length": doc.get("content_length"),
        "full_content_preview": preview,
        "paragraph_count": len(paragraphs),
        "paragraphs": paragraphs,
        "chunk_count": len(chunks),
        "chunks": chunks,
        "case_meta": case_meta,
    }