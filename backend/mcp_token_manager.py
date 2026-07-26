"""MCP token storage and rate limiting."""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from backend.config import BASE

DB_PATH = BASE / "mcp_tokens.db"

# Rate limits
TOKEN_RPM = 100
GLOBAL_RPM = 1000

_lock = threading.Lock()


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _init_db():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mcp_tokens (
                id INTEGER PRIMARY KEY,
                token_hash TEXT UNIQUE NOT NULL,
                name TEXT,
                created_at REAL NOT NULL,
                last_used REAL,
                request_count INTEGER DEFAULT 0,
                revoked_at REAL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mcp_tokens_hash ON mcp_tokens(token_hash)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mcp_call_log (
                id INTEGER PRIMARY KEY,
                token_id INTEGER NOT NULL,
                token_name TEXT,
                created_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mcp_call_log_created ON mcp_call_log(created_at)"
        )
        # Migrate: add name column to pre-existing DBs
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(mcp_tokens)").fetchall()]
        if "name" not in cols:
            conn.execute("ALTER TABLE mcp_tokens ADD COLUMN name TEXT")
        conn.commit()


@contextmanager
def _connect():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@dataclass
class Bucket:
    tokens: float
    last_update: float


_token_buckets: dict[str, Bucket] = {}
_global_bucket = Bucket(GLOBAL_RPM, time.time())


class TokenManager:
    def __init__(self):
        _init_db()

    def create_token(self, name: str = "") -> str:
        """Create a new named token. Returns the raw token (shown once)."""
        raw = secrets.token_hex(32)
        token_hash = _hash(raw)
        with _connect() as conn:
            conn.execute(
                "INSERT INTO mcp_tokens (token_hash, name, created_at) VALUES (?, ?, ?)",
                (token_hash, name.strip(), time.time()),
            )
            conn.commit()
        return raw

    def validate_token(self, token: str) -> bool:
        """Check if token is valid (exists and not revoked)."""
        token_hash = _hash(token)
        with _connect() as conn:
            row = conn.execute(
                "SELECT revoked_at FROM mcp_tokens WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()
            if not row:
                return False
            if row["revoked_at"] is not None:
                return False
        return True

    def record_use(self, token: str) -> None:
        """Increment request count and update last_used."""
        token_hash = _hash(token)
        with _connect() as conn:
            conn.execute(
                "UPDATE mcp_tokens SET request_count = request_count + 1, last_used = ? WHERE token_hash = ?",
                (time.time(), token_hash),
            )
            conn.commit()

    def revoke_token(self, token: str) -> bool:
        """Revoke a token. Returns True if it existed."""
        token_hash = _hash(token)
        with _connect() as conn:
            cur = conn.execute(
                "UPDATE mcp_tokens SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
                (time.time(), token_hash),
            )
            conn.commit()
            return cur.rowcount > 0

    def list_tokens(self) -> list[dict]:
        """List all non-revoked tokens (without hashes)."""
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, created_at, last_used, request_count
                FROM mcp_tokens
                WHERE revoked_at IS NULL
                ORDER BY created_at DESC
                """
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "created_at": r["created_at"],
                    "last_used": r["last_used"],
                    "request_count": r["request_count"],
                }
                for r in rows
            ]

    def log_call(self, token: str) -> None:
        """Record one MCP call event for hall-of-fame time-windowed stats."""
        token_hash = _hash(token)
        with _connect() as conn:
            row = conn.execute(
                "SELECT id, name FROM mcp_tokens WHERE token_hash = ?", (token_hash,)
            ).fetchone()
            if not row:
                return
            conn.execute(
                "INSERT INTO mcp_call_log (token_id, token_name, created_at) VALUES (?, ?, ?)",
                (row["id"], row["name"], time.time()),
            )
            conn.commit()

    def hall_of_fame(self) -> dict:
        """Leaderboard of call counts by token name, over all-time/monthly/daily windows."""
        now = time.time()

        def top(since: float | None) -> list[dict]:
            with _connect() as conn:
                if since is None:
                    rows = conn.execute(
                        """
                        SELECT token_id, token_name, COUNT(*) as count FROM mcp_call_log
                        GROUP BY token_id ORDER BY count DESC LIMIT 10
                        """
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT token_id, token_name, COUNT(*) as count FROM mcp_call_log
                        WHERE created_at >= ? GROUP BY token_id ORDER BY count DESC LIMIT 10
                        """,
                        (since,),
                    ).fetchall()
            return [
                {
                    "name": r["token_name"] or f"Token #{r['token_id']}",
                    "count": r["count"],
                    "token_id": r["token_id"],
                }
                for r in rows
            ]

        return {
            "all_time": top(None),
            "monthly": top(now - 30 * 86400),
            "weekly": top(now - 7 * 86400),
            "daily": top(now - 86400),
        }

    def check_rate_limit(self, token: str) -> tuple[bool, str]:
        """
        Check rate limit for a token.
        Returns (allowed, reason).
        """
        global _global_bucket
        now = time.time()

        with _lock:
            # Per-token bucket
            bucket = _token_buckets.get(token)
            if bucket is None:
                bucket = Bucket(TOKEN_RPM, now)
                _token_buckets[token] = bucket

            elapsed = now - bucket.last_update
            bucket.tokens = min(TOKEN_RPM, bucket.tokens + elapsed * (TOKEN_RPM / 60.0))
            bucket.last_update = now

            if bucket.tokens < 1:
                return False, f"Token rate limit exceeded ({TOKEN_RPM} req/min)"

            bucket.tokens -= 1

            # Global bucket
            elapsed_g = now - _global_bucket.last_update
            _global_bucket.tokens = min(GLOBAL_RPM, _global_bucket.tokens + elapsed_g * (GLOBAL_RPM / 60.0))
            _global_bucket.last_update = now

            if _global_bucket.tokens < 1:
                return False, f"Global rate limit exceeded ({GLOBAL_RPM} req/min)"

            _global_bucket.tokens -= 1

        self.record_use(token)
        self.log_call(token)
        return True, ""


token_manager = TokenManager()
