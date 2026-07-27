"""OAuth 2.1 Token Endpoint with JWT access tokens."""

import hashlib
import os
import secrets
import sqlite3
import time
from urllib.parse import parse_qs

from fastapi import APIRouter
from jose import jwt
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.config import BASE

DB_PATH = BASE / "oauth_codes.db"


def _init_db():
    """Initialize the authorization codes and tokens database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS oauth_authorization_codes (
            code TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            redirect_uri TEXT NOT NULL,
            scope TEXT NOT NULL DEFAULT 'read',
            code_challenge TEXT,
            code_challenge_method TEXT DEFAULT 'S256',
            user_token TEXT NOT NULL,
            expires_at REAL NOT NULL,
            used INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS oauth_access_tokens (
            jti TEXT PRIMARY KEY,
            token_hash TEXT NOT NULL,
            client_id TEXT NOT NULL,
            user_token TEXT NOT NULL,
            scope TEXT NOT NULL DEFAULT 'read',
            issued_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            revoked INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def create_authorization_code(
    code: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    code_challenge: str,
    code_challenge_method: str,
    user_token: str,
    expires_in: int,
):
    """Store an authorization code."""
    _init_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(
            """INSERT INTO oauth_authorization_codes
               (code, client_id, redirect_uri, scope, code_challenge, code_challenge_method, user_token, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (code, client_id, redirect_uri, scope, code_challenge, code_challenge_method, user_token, time.time() + expires_in),
        )
        conn.commit()
    finally:
        conn.close()


def _get_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        secret = secrets.token_hex(48)
        os.environ["JWT_SECRET"] = secret
    return secret


async def token_endpoint(request: Request) -> JSONResponse:
    """POST /oauth/token - Exchange authorization code for access token."""
    # Parse form data (application/x-www-form-urlencoded)
    body = await request.body()
    try:
        params = parse_qs(body.decode("utf-8"))
    except Exception:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Could not parse request body"},
            status_code=400,
        )

    def get_first(key: str) -> str:
        vals = params.get(key, [])
        return vals[0] if vals else ""

    grant_type = get_first("grant_type")
    code = get_first("code")
    redirect_uri = get_first("redirect_uri")
    client_id = get_first("client_id")
    client_secret = get_first("client_secret")
    code_verifier = get_first("code_verifier")

    if grant_type != "authorization_code":
        return JSONResponse(
            {"error": "unsupported_grant_type"},
            status_code=400,
        )

    if not code:
        return JSONResponse(
            {"error": "invalid_request", "error_description": "Missing authorization code"},
            status_code=400,
        )

    # Verify client credentials
    from backend.oauth.registration import verify_client_secret

    if not verify_client_secret(client_id, client_secret):
        return JSONResponse(
            {"error": "invalid_client", "error_description": "Invalid client credentials"},
            status_code=401,
        )

    # Look up authorization code
    _init_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM oauth_authorization_codes WHERE code = ? AND used = 0",
            (code,),
        ).fetchone()

        if not row:
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "Invalid authorization code"},
                status_code=400,
            )

        # Check expiry
        if time.time() > row["expires_at"]:
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "Authorization code expired"},
                status_code=400,
            )

        # Verify redirect URI
        if row["redirect_uri"] != redirect_uri:
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "Redirect URI mismatch"},
                status_code=400,
            )

        # Verify PKCE
        if row["code_challenge"]:
            expected_challenge = hashlib.sha256(code_verifier.encode()).digest()
            expected = (
                base64url_encode(expected_challenge)
                if not code_verifier.startswith("base64url:")
                else code_verifier.replace("base64url:", "")
            )
            # Simple PKCE verification
            digest = hashlib.sha256(code_verifier.encode()).digest()
            computed_challenge = base64url_encode(digest)
            if computed_challenge != row["code_challenge"]:
                return JSONResponse(
                    {"error": "invalid_grant", "error_description": "PKCE verification failed"},
                    status_code=400,
                )

        # Mark code as used
        conn.execute("UPDATE oauth_authorization_codes SET used = 1 WHERE code = ?", (code,))

        # Generate JWT access token
        jti = secrets.token_urlsafe(16)
        now = time.time()
        expires_in = 3600  # 1 hour

        payload = {
            "iss": os.environ.get("OAUTH_ISSUER", str(request.base_url).rstrip("/")),
            "sub": row["user_token"],
            "aud": client_id,
            "exp": now + expires_in,
            "iat": now,
            "jti": jti,
            "scope": row["scope"],
        }

        secret = _get_jwt_secret()
        access_token = jwt.encode(payload, secret, algorithm="HS256")

        # Store token hash for revocation
        token_hash = hashlib.sha256(access_token.encode()).hexdigest()
        conn.execute(
            """INSERT INTO oauth_access_tokens
               (jti, token_hash, client_id, user_token, scope, issued_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (jti, token_hash, client_id, row["user_token"], row["scope"], now, now + expires_in),
        )
        conn.commit()

        return JSONResponse({
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "scope": row["scope"],
        })

    finally:
        conn.close()


def base64url_encode(data: bytes) -> str:
    """Base64url encode without padding."""
    import base64
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


router = APIRouter()
router.add_api_route(
    "/oauth/token",
    token_endpoint,
    methods=["POST"],
    include_in_schema=False,
)