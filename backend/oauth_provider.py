"""OAuth 2.1 authorization server provider for MCP.

Implements the MCP OAuthAuthorizationServerProvider protocol so that
Claude Desktop Connectors can authenticate via OAuth 2.1.

Flow:
  1. /.well-known/oauth-authorization-server — discovery
  2. /oauth/authorize — user authorizes via Azure AD SSO
  3. /oauth/token — exchange auth code for access/refresh tokens
  4. /oauth/register — dynamic client registration (RFC 7591)

Tokens issued here are validated by MCPAuthMiddleware alongside static tokens.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import time
import uuid
from typing import Any
from urllib.parse import urlencode

import sqlite3

from pydantic import AnyHttpUrl, AnyUrl, HttpUrl
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────

BASE_URL = os.environ.get(
    "OAUTH_BASE_URL",
    "https://legislation.scriptkitty.yachts",
)
DB_DIR = os.environ.get("OAUTH_DB_DIR", "/home/harrison/legislation-explorer")
DB_PATH = os.path.join(DB_DIR, "oauth_state.db")
SESSION_SECRET = os.environ.get("SESSION_SECRET", os.environ.get("AZURE_CLIENT_SECRET", "change-me"))

# OAuth token lifetimes
AUTHORIZATION_CODE_TTL = 600       # 10 minutes
ACCESS_TOKEN_TTL = 3600            # 1 hour
REFRESH_TOKEN_TTL = 2592000         # 30 days

# ── DB helpers ────────────────────────────────────────────────────────────────


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


_SQL_SCHEMA = """
CREATE TABLE IF NOT EXISTS oauth_clients (
    client_id TEXT PRIMARY KEY,
    client_secret TEXT,
    client_name TEXT DEFAULT '',
    redirect_uris TEXT DEFAULT '[]',
    grant_types TEXT DEFAULT '["authorization_code","refresh_token"]',
    response_types TEXT DEFAULT '["code"]',
    token_endpoint_auth_method TEXT DEFAULT 'none',
    scope TEXT DEFAULT 'mcp',
    created_at REAL NOT NULL,
    client_id_issued_at INTEGER,
    client_secret_expires_at INTEGER
);

CREATE TABLE IF NOT EXISTS oauth_authorization_codes (
    code TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    code_challenge TEXT,
    code_challenge_method TEXT,
    user_email TEXT NOT NULL,
    user_name TEXT DEFAULT '',
    scopes TEXT DEFAULT 'mcp',
    expires_at REAL NOT NULL,
    used INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS oauth_access_tokens (
    token_hash TEXT PRIMARY KEY,
    token_prefix TEXT NOT NULL,
    client_id TEXT NOT NULL,
    user_email TEXT NOT NULL,
    user_name TEXT DEFAULT '',
    scopes TEXT DEFAULT 'mcp',
    expires_at REAL NOT NULL,
    refresh_token_hash TEXT,
    revoked INTEGER DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS oauth_refresh_tokens (
    token_hash TEXT PRIMARY KEY,
    token_prefix TEXT NOT NULL,
    client_id TEXT NOT NULL,
    user_email TEXT NOT NULL,
    user_name TEXT DEFAULT '',
    scopes TEXT DEFAULT 'mcp',
    expires_at REAL NOT NULL,
    access_token_hash TEXT,
    revoked INTEGER DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_oauth_client_id ON oauth_authorization_codes(client_id);
CREATE INDEX IF NOT EXISTS idx_oauth_token_client ON oauth_access_tokens(client_id);
CREATE INDEX IF NOT EXISTS idx_oauth_token_user ON oauth_access_tokens(user_email);
CREATE INDEX IF NOT EXISTS idx_oauth_refresh_token ON oauth_refresh_tokens(token_hash);
"""


def _init_db() -> None:
    conn = _get_db()
    conn.executescript(_SQL_SCHEMA)
    conn.commit()
    conn.close()


# ── OAuth provider implementation ────────────────────────────────────────────


class OAuthProvider:
    """Implements MCP's OAuthAuthorizationServerProvider protocol.

    Each method maps to a protocol method from the MCP SDK.
    We use our own class (not subclassing the protocol) for simpler
    dependency handling — the protocol is duck-typed.
    """

    def __init__(self) -> None:
        _init_db()

    # ── Helpers ────────────────────────────────────────────────────────────

    def _hash(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def _gen_token(self, prefix: str = "mcp_") -> str:
        return prefix + secrets.token_urlsafe(32)

    def _gen_code(self) -> str:
        return secrets.token_urlsafe(32)

    def _gen_client_id(self) -> str:
        return "cadena_" + secrets.token_urlsafe(16)

    def _gen_client_secret(self) -> str:
        return secrets.token_urlsafe(32)

    # ── Client management ──────────────────────────────────────────────────

    def get_client(self, client_id: str) -> dict[str, Any] | None:
        """Retrieve a registered client by client_id."""
        conn = _get_db()
        row = conn.execute(
            "SELECT * FROM oauth_clients WHERE client_id = ?",
            (client_id,),
        ).fetchone()
        conn.close()
        if not row:
            return None
        return dict(row)

    def register_client(self, client_metadata: dict[str, Any]) -> dict[str, Any]:
        """Register a new OAuth client (RFC 7591 dynamic registration)."""
        client_id = self._gen_client_id()
        client_secret = self._gen_client_secret()

        # Parse redirect URIs
        redirect_uris = client_metadata.get("redirect_uris", [])
        if not redirect_uris:
            raise ValueError("redirect_uris is required")

        conn = _get_db()
        now = int(time.time())
        conn.execute(
            """INSERT INTO oauth_clients
               (client_id, client_secret, client_name, redirect_uris,
                grant_types, response_types, token_endpoint_auth_method,
                scope, created_at, client_id_issued_at, client_secret_expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                client_id,
                client_secret,
                client_metadata.get("client_name", ""),
                json.dumps([str(u) for u in redirect_uris]),
                json.dumps(client_metadata.get("grant_types", ["authorization_code", "refresh_token"])),
                json.dumps(client_metadata.get("response_types", ["code"])),
                client_metadata.get("token_endpoint_auth_method", "none"),
                client_metadata.get("scope", "mcp"),
                time.time(),
                now,
                now + 86400 * 365,  # 1 year
            ),
        )
        conn.commit()
        conn.close()

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "client_id_issued_at": now,
            "client_secret_expires_at": now + 86400 * 365,
            "redirect_uris": redirect_uris,
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "scope": "mcp",
        }

    # ── Authorization code flow ────────────────────────────────────────────

    def create_authorization_code(
        self,
        client_id: str,
        redirect_uri: str,
        user_email: str,
        user_name: str = "",
        scopes: str = "mcp",
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
    ) -> str:
        """Generate and store an authorization code."""
        code = self._gen_code()
        conn = _get_db()
        conn.execute(
            """INSERT INTO oauth_authorization_codes
               (code, client_id, redirect_uri, code_challenge, code_challenge_method,
                user_email, user_name, scopes, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                code,
                client_id,
                redirect_uri,
                code_challenge,
                code_challenge_method,
                user_email,
                user_name,
                scopes,
                time.time() + AUTHORIZATION_CODE_TTL,
            ),
        )
        conn.commit()
        conn.close()
        return code

    def validate_authorization_code(
        self,
        client_id: str,
        code: str,
        code_verifier: str | None = None,
        redirect_uri: str | None = None,
    ) -> dict[str, Any] | None:
        """Validate and consume an authorization code. Returns code data or None."""
        conn = _get_db()
        row = conn.execute(
            "SELECT * FROM oauth_authorization_codes WHERE code = ? AND client_id = ? AND used = 0",
            (code, client_id),
        ).fetchone()
        if not row:
            conn.close()
            return None

        code_data = dict(row)

        # Check expiry
        if code_data["expires_at"] < time.time():
            conn.execute("DELETE FROM oauth_authorization_codes WHERE code = ?", (code,))
            conn.commit()
            conn.close()
            return None

        # PKCE validation
        if code_data["code_challenge"] and code_data["code_challenge_method"] == "S256":
            if not code_verifier:
                conn.close()
                return None
            expected = hashlib.sha256(code_verifier.encode()).digest()
            # base64url-encoded SHA-256 digest
            import base64
            expected_b64 = base64.urlsafe_b64encode(expected).rstrip(b"=").decode()
            if expected_b64 != code_data["code_challenge"]:
                conn.close()
                return None

        # Mark as used
        conn.execute("UPDATE oauth_authorization_codes SET used = 1 WHERE code = ?", (code,))
        conn.commit()
        conn.close()

        return code_data

    # ── Token management ───────────────────────────────────────────────────

    def create_access_token(
        self,
        client_id: str,
        user_email: str,
        user_name: str = "",
        scopes: str = "mcp",
        refresh_token_value: str | None = None,
    ) -> str:
        """Generate and store an access token. Returns the raw token."""
        raw = self._gen_token()
        token_hash = self._hash(raw)
        prefix = raw[:12]
        conn = _get_db()
        conn.execute(
            """INSERT INTO oauth_access_tokens
               (token_hash, token_prefix, client_id, user_email, user_name,
                scopes, expires_at, refresh_token_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                token_hash,
                prefix,
                client_id,
                user_email,
                user_name,
                scopes,
                time.time() + ACCESS_TOKEN_TTL,
                self._hash(refresh_token_value) if refresh_token_value else None,
                time.time(),
            ),
        )
        conn.commit()
        conn.close()
        return raw

    def create_refresh_token(
        self,
        client_id: str,
        user_email: str,
        user_name: str = "",
        scopes: str = "mcp",
        access_token_value: str | None = None,
    ) -> str:
        """Generate and store a refresh token. Returns the raw token."""
        raw = self._gen_token("mcp_ref_")
        token_hash = self._hash(raw)
        prefix = raw[:12]
        conn = _get_db()
        conn.execute(
            """INSERT INTO oauth_refresh_tokens
               (token_hash, token_prefix, client_id, user_email, user_name,
                scopes, expires_at, access_token_hash, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                token_hash,
                prefix,
                client_id,
                user_email,
                user_name,
                scopes,
                time.time() + REFRESH_TOKEN_TTL,
                self._hash(access_token_value) if access_token_value else None,
                time.time(),
            ),
        )
        conn.commit()
        conn.close()
        return raw

    def load_access_token(self, token: str) -> dict[str, Any] | None:
        """Validate an access token and return its data."""
        token_hash = self._hash(token)
        conn = _get_db()
        row = conn.execute(
            "SELECT * FROM oauth_access_tokens WHERE token_hash = ? AND revoked = 0",
            (token_hash,),
        ).fetchone()
        conn.close()
        if not row:
            return None
        data = dict(row)
        if data["expires_at"] < time.time():
            return None
        return data

    def exchange_refresh_token(self, refresh_token: str) -> dict[str, Any] | None:
        """Validate and rotate a refresh token. Returns new token pair data."""
        token_hash = self._hash(refresh_token)
        conn = _get_db()
        row = conn.execute(
            "SELECT * FROM oauth_refresh_tokens WHERE token_hash = ? AND revoked = 0",
            (token_hash,),
        ).fetchone()
        if not row:
            conn.close()
            return None
        data = dict(row)
        if data["expires_at"] < time.time():
            conn.close()
            return None

        # Revoke old refresh token
        conn.execute("UPDATE oauth_refresh_tokens SET revoked = 1 WHERE token_hash = ?", (token_hash,))
        conn.commit()
        conn.close()

        # Issue new tokens
        new_access = self.create_access_token(
            client_id=data["client_id"],
            user_email=data["user_email"],
            user_name=data["user_name"],
            scopes=data["scopes"],
        )
        new_refresh = self.create_refresh_token(
            client_id=data["client_id"],
            user_email=data["user_email"],
            user_name=data["user_name"],
            scopes=data["scopes"],
            access_token_value=new_access,
        )

        return {
            "access_token": new_access,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_TTL,
            "refresh_token": new_refresh,
            "scope": data["scopes"],
        }

    def revoke_token(self, token: str) -> None:
        """Revoke an access or refresh token."""
        token_hash = self._hash(token)
        conn = _get_db()
        conn.execute("UPDATE oauth_access_tokens SET revoked = 1 WHERE token_hash = ?", (token_hash,))
        conn.execute("UPDATE oauth_refresh_tokens SET revoked = 1 WHERE token_hash = ?", (token_hash,))
        conn.commit()
        conn.close()

    def revoke_all_for_user(self, user_email: str) -> None:
        """Revoke all tokens for a given user."""
        conn = _get_db()
        conn.execute(
            "UPDATE oauth_access_tokens SET revoked = 1 WHERE user_email = ?",
            (user_email,),
        )
        conn.execute(
            "UPDATE oauth_refresh_tokens SET revoked = 1 WHERE user_email = ?",
            (user_email,),
        )
        conn.commit()
        conn.close()


# ── Singletons ────────────────────────────────────────────────────────────────

provider = OAuthProvider()


# ── Route helpers ─────────────────────────────────────────────────────────────


def get_oauth_metadata() -> dict[str, Any]:
    """Return OAuth 2.1 authorization server metadata (RFC 8414)."""
    return {
        "issuer": f"{BASE_URL}",
        "authorization_endpoint": f"{BASE_URL}/oauth/authorize",
        "token_endpoint": f"{BASE_URL}/oauth/token",
        "registration_endpoint": f"{BASE_URL}/oauth/register",
        "scopes_supported": ["mcp"],
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["none"],
        "code_challenge_methods_supported": ["S256"],
        "revocation_endpoint": f"{BASE_URL}/oauth/revoke",
    }


async def handle_well_known(request: Request) -> JSONResponse:
    """GET /.well-known/oauth-authorization-server"""
    return JSONResponse(get_oauth_metadata())


async def handle_register(request: Request) -> JSONResponse:
    """POST /oauth/register — dynamic client registration."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    try:
        client_info = provider.register_client(body)
    except ValueError as e:
        return JSONResponse({"error": "invalid_client_metadata", "error_description": str(e)}, status_code=400)

    return JSONResponse(client_info, status_code=201)


async def handle_authorize(request: Request) -> Response:
    """GET /oauth/authorize — authorization endpoint.

    Flow:
      1. Client (Claude Desktop) redirects user here with query params
      2. If user not authenticated via Azure AD, redirect to login
      3. After auth, user gives consent
      4. Redirect back to client's redirect_uri with auth code
    """
    # Parse required params
    client_id = request.query_params.get("client_id")
    redirect_uri = request.query_params.get("redirect_uri")
    response_type = request.query_params.get("response_type")
    state = request.query_params.get("state")
    code_challenge = request.query_params.get("code_challenge")
    code_challenge_method = request.query_params.get("code_challenge_method", "S256")
    scope = request.query_params.get("scope", "mcp")

    # Validate
    errors = []
    if not client_id:
        errors.append("client_id is required")
    if not redirect_uri:
        errors.append("redirect_uri is required")
    if response_type != "code":
        errors.append("response_type must be 'code'")

    if errors:
        error_url = f"{redirect_uri or BASE_URL}?error=invalid_request&error_description={' '.join(errors)}"
        if state:
            error_url += f"&state={state}"
        return RedirectResponse(url=error_url, status_code=303)

    # Validate client exists
    client = provider.get_client(client_id)
    if not client:
        error_url = f"{redirect_uri}?error=invalid_client&error_description=Unknown client"
        if state:
            error_url += f"&state={state}"
        return RedirectResponse(url=error_url, status_code=303)

    # Validate redirect URI
    import json as _json
    registered_uris = _json.loads(client.get("redirect_uris", "[]"))
    if redirect_uri not in registered_uris:
        error_url = f"{redirect_uri}?error=invalid_request&error_description=redirect_uri not registered"
        if state:
            error_url += f"&state={state}"
        return RedirectResponse(url=error_url, status_code=303)

    # Validate PKCE
    if code_challenge and code_challenge_method not in ("S256", "plain"):
        error_url = f"{redirect_uri}?error=invalid_request&error_description=Unsupported code_challenge_method"
        if state:
            error_url += f"&state={state}"
        return RedirectResponse(url=error_url, status_code=303)

    # Check if user is already authenticated via Azure AD session
    from backend.auth import decode_session_token
    session_token = request.cookies.get("session")
    user = decode_session_token(session_token) if session_token else None

    if not user:
        # Redirect to Azure AD login, with a state param pointing back here
        from urllib.parse import quote
        next_url = f"{BASE_URL}/oauth/authorize?client_id={client_id}&redirect_uri={quote(redirect_uri)}&response_type=code"
        if state:
            next_url += f"&state={state}"
        if code_challenge:
            next_url += f"&code_challenge={code_challenge}&code_challenge_method={code_challenge_method}"
        if scope:
            next_url += f"&scope={scope}"
        return RedirectResponse(
            url=f"{BASE_URL}/auth/login?next={quote(next_url)}",
            status_code=303,
        )

    # User is authenticated — issue authorization code
    user_email = user.get("email", "") or user.get("sub", "")
    user_name = user.get("name", "")

    code = provider.create_authorization_code(
        client_id=client_id,
        redirect_uri=redirect_uri,
        user_email=user_email,
        user_name=user_name,
        scopes=scope,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method if code_challenge else None,
    )

    # Redirect back to client with the code
    result_url = f"{redirect_uri}?code={code}"
    if state:
        result_url += f"&state={state}"
    if scope:
        result_url += f"&scope={scope}"

    return RedirectResponse(url=result_url, status_code=303)


async def handle_token(request: Request) -> JSONResponse:
    """POST /oauth/token — exchange authorization code or refresh token."""
    try:
        body = await request.form()
    except Exception:
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    grant_type = body.get("grant_type")
    client_id = body.get("client_id", "")

    if grant_type == "authorization_code":
        code = body.get("code")
        code_verifier = body.get("code_verifier")
        redirect_uri = body.get("redirect_uri")

        if not code:
            return JSONResponse({"error": "invalid_request", "error_description": "code is required"}, status_code=400)
        if not client_id:
            return JSONResponse({"error": "invalid_request", "error_description": "client_id is required"}, status_code=400)

        # Validate the authorization code
        code_data = provider.validate_authorization_code(
            client_id=client_id,
            code=code,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
        )
        if not code_data:
            return JSONResponse({"error": "invalid_grant", "error_description": "Invalid or expired authorization code"}, status_code=400)

        # Issue tokens
        access_token = provider.create_access_token(
            client_id=client_id,
            user_email=code_data["user_email"],
            user_name=code_data["user_name"],
            scopes=code_data["scopes"],
        )
        refresh_token = provider.create_refresh_token(
            client_id=client_id,
            user_email=code_data["user_email"],
            user_name=code_data["user_name"],
            scopes=code_data["scopes"],
            access_token_value=access_token,
        )

        return JSONResponse({
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_TTL,
            "refresh_token": refresh_token,
            "scope": code_data["scopes"],
        })

    elif grant_type == "refresh_token":
        refresh_token_value = body.get("refresh_token")
        if not refresh_token_value:
            return JSONResponse({"error": "invalid_request", "error_description": "refresh_token is required"}, status_code=400)

        result = provider.exchange_refresh_token(refresh_token_value)
        if not result:
            return JSONResponse({"error": "invalid_grant", "error_description": "Invalid or expired refresh token"}, status_code=400)

        return JSONResponse(result)

    else:
        return JSONResponse(
            {"error": "unsupported_grant_type", "error_description": f"Grant type '{grant_type}' not supported"},
            status_code=400,
        )


async def handle_revoke(request: Request) -> JSONResponse:
    """POST /oauth/revoke — revoke an access or refresh token."""
    try:
        body = await request.form()
    except Exception:
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    token = body.get("token")
    if not token:
        return JSONResponse({"error": "invalid_request", "error_description": "token is required"}, status_code=400)

    provider.revoke_token(token)
    return JSONResponse({}, status_code=200)

from jose import jwt as pyjwt

async def handle_authorize_consent(request: Request) -> JSONResponse:
    """GET /oauth/consent — after Azure AD login, show consent page.

    This is called from the auth login callback — user has authenticated,
    now we need them to consent before issuing the authorization code.
    """
    try:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        # Validate the session/jwt
        session_token = auth_header[7:]
        user = None
        try:
            user = pyjwt.decode(session_token, SESSION_SECRET, algorithms=["HS256"])
        except Exception:
            return JSONResponse({"error": "Invalid session"}, status_code=401)

        if not user:
            return JSONResponse({"error": "Not authenticated"}, status_code=401)

        state = request.query_params.get("state")
        if not state:
            return JSONResponse({"error": "missing state"}, status_code=400)

        # Decode state to get original authorize params
        try:
            state_data = json.loads(state)
        except Exception:
            return JSONResponse({"error": "invalid state"}, status_code=400)

        code = provider.create_authorization_code(
            client_id=state_data["client_id"],
            redirect_uri=state_data["redirect_uri"],
            user_email=user.get("email", ""),
            user_name=user.get("name", ""),
            scopes=state_data.get("scope", "mcp"),
            code_challenge=state_data.get("code_challenge"),
            code_challenge_method=state_data.get("code_challenge_method"),
        )

        result_url = f"{state_data['redirect_uri']}?code={code}"
        if state_data.get("client_state"):
            result_url += f"&state={state_data['client_state']}"

        return RedirectResponse(url=result_url, status_code=303)

    except Exception as e:
        logger.exception("Consent failed")
        return JSONResponse({"error": "server_error", "error_description": str(e)}, status_code=500)
