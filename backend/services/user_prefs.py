"""User preferences service — SQLite-backed per-user settings."""
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from backend.config import BASE

DB_PATH = BASE / "user_prefs.db"

# Default preferences
DEFAULT_PREFS: dict[str, Any] = {
    "display_name": "",
    "default_act": "itaa-1997",
    "theme": "dark",
    "accent_color": "#279e88",
    "text_color": "#aebec2",
    "bg_color": "#0a1214",
    "heading_font": "Montserrat",
    "body_font": "Lora",
}


def _init():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                email TEXT PRIMARY KEY,
                display_name TEXT DEFAULT '',
                default_act TEXT DEFAULT 'itaa-1997',
                theme TEXT DEFAULT 'dark',
                accent_color TEXT DEFAULT '#279e88',
                text_color TEXT DEFAULT '#aebec2',
                bg_color TEXT DEFAULT '#0a1214',
                heading_font TEXT DEFAULT 'Montserrat',
                body_font TEXT DEFAULT 'Lora',
                updated_at REAL NOT NULL
            )
            """
        )
        conn.commit()

    # Migrate existing databases: add columns if missing
    for col, default in [("text_color", "#aebec2"), ("bg_color", "#0a1214")]:
        try:
            with _connect() as conn:
                conn.execute(
                    f"ALTER TABLE user_preferences ADD COLUMN {col} TEXT DEFAULT '{default}'"
                )
                conn.commit()
        except Exception:
            pass


@contextmanager
def _connect():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_prefs(email: str) -> dict[str, Any]:
    """Get a user's preferences, merged with defaults for any missing fields."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM user_preferences WHERE email = ?", (email,)
        ).fetchone()
    if not row:
        return {**DEFAULT_PREFS, "email": email}
    return {
        "email": row["email"],
        "display_name": row["display_name"] or "",
        "default_act": row["default_act"] or DEFAULT_PREFS["default_act"],
        "theme": row["theme"] or DEFAULT_PREFS["theme"],
        "accent_color": row["accent_color"] or DEFAULT_PREFS["accent_color"],
        "text_color": row["text_color"] or DEFAULT_PREFS["text_color"],
        "bg_color": row["bg_color"] or DEFAULT_PREFS["bg_color"],
        "heading_font": row["heading_font"] or DEFAULT_PREFS["heading_font"],
        "body_font": row["body_font"] or DEFAULT_PREFS["body_font"],
    }


def update_prefs(email: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Update a user's preferences (partial merge) and return the full prefs."""
    current = get_prefs(email)
    current.update(updates)
    current["updated_at"] = time.time()

    valid_themes = {"dark", "light"}
    if current["theme"] not in valid_themes:
        current["theme"] = DEFAULT_PREFS["theme"]

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO user_preferences (email, display_name, default_act, theme,
                accent_color, text_color, bg_color, heading_font, body_font, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                display_name = excluded.display_name,
                default_act = excluded.default_act,
                theme = excluded.theme,
                accent_color = excluded.accent_color,
                text_color = excluded.text_color,
                bg_color = excluded.bg_color,
                heading_font = excluded.heading_font,
                body_font = excluded.body_font,
                updated_at = excluded.updated_at
            """,
            (
                current["email"],
                current["display_name"],
                current["default_act"],
                current["theme"],
                current["accent_color"],
                current["text_color"],
                current["bg_color"],
                current["heading_font"],
                current["body_font"],
                current["updated_at"],
            ),
        )
        conn.commit()
    return get_prefs(email)


def reset_prefs(email: str) -> dict[str, Any]:
    """Reset a user's preferences to defaults."""
    defaults = {**DEFAULT_PREFS, "email": email, "updated_at": time.time()}
    with _connect() as conn:
        conn.execute(
            """INSERT INTO user_preferences (email, display_name, default_act, theme,
                accent_color, text_color, bg_color, heading_font, body_font, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                display_name = excluded.display_name,
                default_act = excluded.default_act,
                theme = excluded.theme,
                accent_color = excluded.accent_color,
                text_color = excluded.text_color,
                bg_color = excluded.bg_color,
                heading_font = excluded.heading_font,
                body_font = excluded.body_font,
                updated_at = excluded.updated_at
            """,
            (
                defaults["email"],
                defaults["display_name"],
                defaults["default_act"],
                defaults["theme"],
                defaults["accent_color"],
                defaults["text_color"],
                defaults["bg_color"],
                defaults["heading_font"],
                defaults["body_font"],
                defaults["updated_at"],
            ),
        )
        conn.commit()
    return get_prefs(email)


def get_all_prefs() -> list[dict[str, Any]]:
    """Get all users' preferences (admin only)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM user_preferences ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


_init()