"""OAuth 2.1 Dynamic Client Registration (RFC 7591)."""

import hashlib
import secrets

from fastapi import APIRouter
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.config import BASE

DB_PATH = BASE / "oauth_clients.db"


def _init_clients_db():
    """Initialize the OAuth clients database."""
    import sqlite3

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS oauth_clients (
            id TEXT PRIMARY KEY,
            client_secret TEXT NOT NULL,
            client_name TEXT NOT NULL,
            redirect_uris TEXT NOT NULL,
            grant_types TEXT NOT NULL DEFAULT '["authorization_code"]',
            response_types TEXT NOT NULL DEFAULT '["code"]',
            scope TEXT NOT NULL DEFAULT 'read',
            client_id_issued_at REAL NOT NULL,
            client_secret_expires_at REAL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


class RegisterClientRequest(BaseModel):
    client_name: str = "MCP Client"
    redirect_uris: list[str]
    grant_types: list[str] = ["authorization_code"]
    response_types: list[str] = ["code"]
    scope: str = "read"


async def register_client(request: Request, body: RegisterClientRequest) -> JSONResponse:
    """Register a new OAuth client (Dynamic Client Registration)."""
    import json
    import sqlite3
    import time

    # Validate redirect URIs
    for uri in body.redirect_uris:
        if uri.startswith("http://") and "localhost" not in uri and "127.0.0.1" not in uri:
            return JSONResponse(
                {"error": "invalid_redirect_uri", "error_description": "Only HTTPS or localhost redirect URIs are allowed"},
                status_code=400,
            )

    client_id = secrets.token_urlsafe(32)
    client_secret = secrets.token_urlsafe(48)

    _init_clients_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(
            """INSERT INTO oauth_clients
               (id, client_secret, client_name, redirect_uris, grant_types, response_types, scope, client_id_issued_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                client_id,
                _hash_secret(client_secret),
                body.client_name,
                json.dumps(body.redirect_uris),
                json.dumps(body.grant_types),
                json.dumps(body.response_types),
                body.scope,
                time.time(),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return JSONResponse(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_name": body.client_name,
            "redirect_uris": body.redirect_uris,
            "grant_types": body.grant_types,
            "response_types": body.response_types,
            "token_endpoint_auth_method": "client_secret_post",
            "scope": body.scope,
        },
        status_code=201,
    )


def get_client(client_id: str) -> dict | None:
    """Look up an OAuth client by ID."""
    import json
    import sqlite3

    _init_clients_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM oauth_clients WHERE id = ?", (client_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "client_secret_hash": row["client_secret"],
            "client_name": row["client_name"],
            "redirect_uris": json.loads(row["redirect_uris"]),
            "grant_types": json.loads(row["grant_types"]),
            "response_types": json.loads(row["response_types"]),
            "scope": row["scope"],
            "active": bool(row["active"]),
        }
    finally:
        conn.close()


def verify_client_secret(client_id: str, client_secret: str) -> bool:
    """Verify a client secret."""
    client = get_client(client_id)
    if not client:
        return False
    return client["client_secret_hash"] == _hash_secret(client_secret)


router = APIRouter()
router.add_api_route(
    "/oauth/register",
    register_client,
    methods=["POST"],
    include_in_schema=False,
)