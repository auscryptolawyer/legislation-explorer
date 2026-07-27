"""SQLite FTS5 search service."""
from __future__ import annotations

import re
import sqlite3
import logging
from contextlib import contextmanager
from typing import Any

from backend.config import DATA_DIR, RULING_DIR, SEARCH_DB
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
    """Build or rebuild the FTS5 search index from all markdown sections and rulings."""
    with search_conn() as conn:
        # --- Sections FTS ---
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

        # --- Rulings FTS ---
        conn.execute("DROP TABLE IF EXISTS rulings_fts")
        conn.execute("""
            CREATE VIRTUAL TABLE rulings_fts USING fts5(
                citation, title, content,
                tokenize='porter'
            )
        """)
        conn.execute("DROP TABLE IF EXISTS rulings_meta")
        conn.execute("""
            CREATE TABLE rulings_meta (
                citation TEXT UNIQUE, title TEXT, year INTEGER, ruling_type TEXT
            )
        """)

        ruled_seen: set[str] = set()
        for f in sorted(RULING_DIR.glob("*.txt")):
            if f.name.endswith(".meta.json") or f.name.startswith("."):
                continue
            citation = f.stem
            if citation in ruled_seen:
                continue
            ruled_seen.add(citation)

            title = citation
            year = 0
            ruling_type = ""
            m = re.match(r'^([A-Za-z]+)_(\d{2,4})_(\d+)', f.stem)
            if m:
                ruling_type = m.group(1).upper()
                year = int(m.group(2))
                if year < 100:
                    year += 1900 if year >= 90 else 2000

            meta_path = f.with_suffix(f.suffix + ".meta.json")
            if not meta_path.exists():
                meta_path = f.parent / (f.stem + ".txt.meta.json")
            if meta_path.exists():
                import json
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                title = meta.get("title", citation)

            content_raw = f.read_text(encoding="utf-8", errors="replace")
            content = re.sub(r'[#*`_\[\]\(\)]', ' ', content_raw)
            content = re.sub(r'\s+', ' ', content).strip()[:50000]

            conn.execute(
                "INSERT INTO rulings_fts (citation, title, content) VALUES (?, ?, ?)",
                (citation, title, content)
            )
            conn.execute(
                "INSERT INTO rulings_meta (citation, title, year, ruling_type) VALUES (?, ?, ?, ?)",
                (citation, title, year, ruling_type)
            )

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

    content = re.sub(r'[#*`_\[\]\(\)]', ' ', content_body)
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

    # If query looks like a section number, exact-match it to rank 1.
    # We use a separate SQL query (not limited) to find the exact section
    # so it can be promoted even if the main FTS results don't include it.
    section_re = re.match(r'^(\d+[A-Z]?-\d+(?:[A-Za-z]*(?:\(\d+(?:\)[a-z])?\))?)?)$', q.strip())
    if section_re:
        section_id = section_re.group(1)
        # Find the exact match via a separate unlimited query
        with search_conn() as conn:
            if act:
                exact = conn.execute(
                    "SELECT act, section, title, part, division, "
                    "snippet(sections_fts, 3, '<mark>', '</mark>', '...', 32) as snippet "
                    "FROM sections_fts JOIN sections_meta m USING(act, section) "
                    "WHERE sections_fts.act = ? AND sections_fts.section = ?",
                    (act, section_id)
                ).fetchone()
            else:
                exact = conn.execute(
                    "SELECT act, section, title, part, division, "
                    "snippet(sections_fts, 3, '<mark>', '</mark>', '...', 32) as snippet "
                    "FROM sections_fts JOIN sections_meta m USING(act, section) "
                    "WHERE sections_fts.section = ?",
                    (section_id,)
                ).fetchone()
        if exact:
            # Prepend the exact match, avoiding duplicates
            results = [
                {
                    "act": exact["act"],
                    "section": exact["section"],
                    "title": exact["title"],
                    "part": exact["part"],
                    "division": exact["division"],
                    "snippet": exact["snippet"] or "",
                }
            ] + [
                r for r in results
                if not (r["act"] == exact["act"] and r["section"] == exact["section"])
            ]

    return results[:limit]


def search_rulings(q: str, limit: int = 20) -> list[dict]:
    """Search rulings using FTS5 BM25 ranking."""
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
        sql = """
            SELECT rulings_fts.citation, rulings_fts.title,
                   m.year, m.ruling_type,
                   rank, snippet(rulings_fts, 2, '<mark>', '</mark>', '...', 32) as snippet
            FROM rulings_fts
            JOIN rulings_meta m ON rulings_fts.citation = m.citation
            WHERE rulings_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """
        rows = conn.execute(sql, (q_clean, limit)).fetchall()

    results = []
    for row in rows:
        results.append({
            "act": "rulings",
            "section": row["citation"],
            "title": row["title"],
            "citation": row["citation"],
            "year": row["year"],
            "ruling_type": row["ruling_type"],
            "snippet": row["snippet"] or "",
        })
    return results
