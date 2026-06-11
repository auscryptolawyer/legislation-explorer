"""SQLite FTS5 search service."""
from __future__ import annotations

import re
import sqlite3
import logging
from contextlib import contextmanager
from typing import Any

from backend.config import DATA_DIR, SEARCH_DB
from backend.services.data_loader import load_tree, get_act_section_content

logger = logging.getLogger(__name__)


@contextmanager
def search_conn():
    """Yield a fresh SQLite connection (per-request safety)."""
    conn = sqlite3.connect(str(SEARCH_DB))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_search_index() -> None:
    """Build or rebuild the FTS5 search index from all markdown sections."""
    with search_conn() as conn:
        conn.execute("DROP TABLE IF EXISTS sections_fts")
        conn.execute("""
            CREATE VIRTUAL TABLE sections_fts USING fts5(
                act, section, title, content,
                tokenize='porter'
            )
        """)
        conn.execute("DROP TABLE IF EXISTS sections_meta")
        conn.execute("""
            CREATE TABLE sections_meta (
                act TEXT, section TEXT, title TEXT, part TEXT, division TEXT,
                UNIQUE (act, section)
            )
        """)
        conn.execute("CREATE INDEX idx_meta_act_section ON sections_meta(act, section)")

        # Track (act, section_id) pairs already indexed so each section is
        # inserted exactly once (first occurrence wins for part/division
        # metadata).  Some tree.json files list the same section under
        # multiple parts/divisions, which previously produced duplicate rows
        # in both sections_fts and sections_meta and multiplied search hits.
        seen: set[tuple[str, str]] = set()

        for act_dir in DATA_DIR.iterdir():
            if not act_dir.is_dir() or not (act_dir / "tree.json").exists():
                continue
            act = act_dir.name
            tree = load_tree(act)
            for part in tree.get("parts", []):
                part_id = part.get("id", "")
                for sec in part.get("sections", []):
                    _index_section(conn, act, sec, part_id, "", seen)
                for div in part.get("divisions", []):
                    div_id = div.get("id", "")
                    for sec in div.get("sections", []):
                        _index_section(conn, act, sec, part_id, div_id, seen)
                    for sub in div.get("subdivisions", []):
                        for sec in sub.get("sections", []):
                            _index_section(conn, act, sec, part_id, div_id, seen)

        conn.commit()
    logger.info(f"Search index built: {SEARCH_DB}")


def _index_section(
    conn: sqlite3.Connection,
    act: str,
    sec: dict,
    part: str,
    division: str,
    seen: set[tuple[str, str]],
) -> None:
    sec_id = sec["id"]
    key = (act, sec_id)
    if key in seen:
        return
    seen.add(key)

    title = sec.get("title", "")
    try:
        fm, content_body = get_act_section_content(act, sec_id)
    except Exception:
        logger.exception(f"Error getting section content for {act}/{sec_id}")
        content_body = ""

    content = re.sub(r'[#*`_[\]\(\)]', ' ', content_body)
    content = re.sub(r'\s+', ' ', content).strip()[:50000]

    conn.execute(
        "INSERT INTO sections_fts (act, section, title, content) VALUES (?, ?, ?, ?)",
        (act, sec_id, title, content)
    )
    conn.execute(
        "INSERT INTO sections_meta (act, section, title, part, division) VALUES (?, ?, ?, ?, ?)",
        (act, sec_id, title, part, division)
    )


def search_sections(q: str, act: str | None = None, limit: int = 50) -> list[dict]:
    """Search using SQLite FTS5 with BM25 ranking."""
    # Quote each token as an FTS5 string literal so bare '-', '(', etc. are
    # treated as content, not FTS5 query syntax (column filters/operators).
    tokens = q.split()
    if not tokens:
        return []
    quoted = []
    for tok in tokens:
        if tok.endswith('*') and len(tok) > 1:
            inner = tok[:-1].replace('"', '""')
            quoted.append(f'"{inner}"*')
        else:
            quoted.append('"' + tok.replace('"', '""') + '"')
    q_clean = ' '.join(quoted)

    with search_conn() as conn:
        if act:
            sql = """
                SELECT sections_fts.act, sections_fts.section, sections_fts.title,
                       m.part, m.division,
                       rank, snippet(sections_fts, 3, '<mark>', '</mark>', '...', 32) as snippet
                FROM sections_fts
                JOIN sections_meta m ON sections_fts.act = m.act AND sections_fts.section = m.section
                WHERE sections_fts MATCH ? AND sections_fts.act = ?
                ORDER BY rank
                LIMIT ?
            """
            rows = conn.execute(sql, (q_clean, act, limit)).fetchall()
        else:
            sql = """
                SELECT sections_fts.act, sections_fts.section, sections_fts.title,
                       m.part, m.division,
                       rank, snippet(sections_fts, 3, '<mark>', '</mark>', '...', 32) as snippet
                FROM sections_fts
                JOIN sections_meta m ON sections_fts.act = m.act AND sections_fts.section = m.section
                WHERE sections_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            rows = conn.execute(sql, (q_clean, limit)).fetchall()

    results = []
    for row in rows:
        results.append({
            "act": row["act"],
            "section": row["section"],
            "title": row["title"],
            "part": row["part"],
            "division": row["division"],
            "snippet": row["snippet"] or "",
        })
    return results
