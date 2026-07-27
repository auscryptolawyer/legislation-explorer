"""OAuth 2.1 JWT validation middleware for MCP requests."""

import hashlib
import hmac
import os
from typing import Awaitable, Callable

from jose import JWTError, jwt
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class OAuth2Middleware:
    """ASGI middleware for dual-mode authentication: JWT OR legacy token.

    Validates JWT access tokens from OAuth 2.1 flow, falling back to
    legacy Bearer token authentication for backward compatibility.
    """

    def __init__(
        self,
        app: Callable[[dict, Callable, Callable], Awaitable[None]],
        public_paths: list[str] | None = None,
    ):
        self.app = app
        self.public_paths = public_paths or [
            "/health",
            "/.well-known/oauth-authorization-server",
            "/.well-known/oauth-protected-resource",
            "/oauth/register",
            "/oauth/authorize",
            "/oauth/token",
            "/auth/login",
            "/auth/callback",
            "/auth/logout",
            "/auth/me",
            "/",
            "/favicon.ico",
        ]

    async def __call__(
        self,
        scope: dict,
        receive: Callable,
        send: Callable,
    ) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Check if path is public
        path = scope.get("path", "")
        if any(path.startswith(public) for public in self.public_paths):
            await self.app(scope, receive, send)
            return

        # Skip static assets
        if path.startswith("/assets/") or path.startswith("/static/"):
            await self.app(scope, receive, send)
            return

        # Extract token from Authorization header or query param
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode()

        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

        # Also check query param for ?token= (legacy)
        if not token:
            request = Request(scope, receive)
            token = request.query_params.get("token", "")

        if not token:
            await self._send_unauthorized(send, "Missing or invalid Authorization header")
            return

        # Try JWT validation first
        jwt_valid, jwt_payload = await self._validate_jwt(token)
        if jwt_valid:
            scope["user"] = {
                "user_token": jwt_payload["sub"],
                "client_id": jwt_payload["aud"],
                "scope": jwt_payload.get("scope", "read"),
                "auth_method": "oauth2",
            }
            await self.app(scope, receive, send)
            return

        # Fall back to legacy token validation
        legacy_valid = await self._validate_legacy_token(token)
        if legacy_valid:
            scope["user"] = {
                "user_token": token,
                "auth_method": "legacy",
            }
            await self.app(scope, receive, send)
            return

        # Both validations failed
        await self._send_unauthorized(send, "Invalid or expired token")

    async def _validate_jwt(self, token: str) -> tuple[bool, dict]:
        try:
            secret = os.environ.get("JWT_SECRET")
            if not secret:
                return False, {}

            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"verify_exp": True},
            )

            # Check if token is revoked in database
            from backend.oauth.token import DB_PATH as OAUTH_DB_PATH
            import sqlite3

            token_hash = hashlib.sha256(token.encode()).hexdigest()
            conn = sqlite3.connect(str(OAUTH_DB_PATH))
            try:
                row = conn.execute(
                    "SELECT revoked FROM oauth_access_tokens WHERE token_hash = ?",
                    (token_hash,),
                ).fetchone()
                if row and row[0]:
                    return False, {}
            finally:
                conn.close()

            return True, payload

        except JWTError:
            return False, {}
        except Exception:
            return False, {}

    async def _validate_legacy_token(self, token: str) -> bool:
        # Check MCP_AUTH_TOKEN env var
        legacy_token = os.environ.get("MCP_AUTH_TOKEN", "")
        if legacy_token and hmac.compare_digest(token, legacy_token):
            return True

        # Check BEARER_TOKEN config
        from backend.config import BEARER_TOKEN
        if BEARER_TOKEN and hmac.compare_digest(token, BEARER_TOKEN):
            return True

        # Check against SQLite token manager
        from backend.mcp_token_manager import token_manager
        if token_manager.validate_token(token):
            return True

        return False

    async def _send_unauthorized(self, send: Callable, message: str) -> None:
        response = JSONResponse(
            {"error": "unauthorized", "error_description": message},
            status_code=401,
            headers={"WWW-Authenticate": 'Bearer realm="legislation-explorer"'},
        )
        await response({"type": "http"}, lambda: None, send)