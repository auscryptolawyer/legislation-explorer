"""OAuth 2.1 Authorization Endpoint with user login and consent."""

import os
import secrets
from pathlib import Path
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response


TEMPLATE_DIR = Path(__file__).parent / "templates"


def load_template(name: str) -> str:
    """Load HTML template from templates directory."""
    template_path = TEMPLATE_DIR / name
    if not template_path.exists():
        return f"<html><body><h1>Template not found: {name}</h1></body></html>"
    return template_path.read_text()


async def authorize_get(request: Request) -> Response:
    """GET /oauth/authorize - Show login/consent form."""
    response_type = request.query_params.get("response_type")
    client_id = request.query_params.get("client_id")
    redirect_uri = request.query_params.get("redirect_uri")
    scope = request.query_params.get("scope", "read")
    state = request.query_params.get("state", "")
    code_challenge = request.query_params.get("code_challenge")
    code_challenge_method = request.query_params.get("code_challenge_method")

    # Validate parameters
    if not all([response_type, client_id, redirect_uri]):
        return HTMLResponse(
            "<html><body><h1>Error</h1><p>Missing required parameters</p></body></html>",
            status_code=400,
        )

    if response_type != "code":
        return HTMLResponse(
            "<html><body><h1>Error</h1><p>Unsupported response_type. Only 'code' is supported.</p></body></html>",
            status_code=400,
        )

    # OAuth 2.1 requires PKCE
    if not code_challenge or not code_challenge_method:
        return HTMLResponse(
            "<html><body><h1>Error</h1><p>PKCE is required (code_challenge and code_challenge_method)</p></body></html>",
            status_code=400,
        )

    if code_challenge_method != "S256":
        return HTMLResponse(
            "<html><body><h1>Error</h1><p>Only S256 code_challenge_method is supported</p></body></html>",
            status_code=400,
        )

    # Validate client
    from backend.oauth.registration import get_client

    client = get_client(client_id)
    if not client:
        return HTMLResponse(
            "<html><body><h1>Error</h1><p>Invalid client_id</p></body></html>",
            status_code=400,
        )

    if not client["active"]:
        return HTMLResponse(
            "<html><body><h1>Error</h1><p>Client is inactive</p></body></html>",
            status_code=400,
        )

    # Validate redirect_uri
    # Allow any localhost/127.0.0.1 redirect URI regardless of registration
    # (Claude Desktop uses dynamic localhost ports for OAuth callbacks)
    is_localhost = redirect_uri.startswith("http://localhost:") or redirect_uri.startswith("http://127.0.0.1:")
    if not is_localhost and redirect_uri not in client["redirect_uris"]:
        return HTMLResponse(
            "<html><body><h1>Error</h1><p>Invalid redirect_uri</p></body></html>",
            status_code=400,
        )

    # Check if user is already authenticated (session cookie)
    user_token = request.cookies.get("user_token")

    if not user_token:
        # Show login form
        template = load_template("login.html")
        auth_params = urlencode({
            "response_type": response_type,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
        })
        html = template.replace("{{client_name}}", client["client_name"]).replace(
            "{{auth_params}}", auth_params
        )
        return HTMLResponse(html)

    # User authenticated - show consent form
    template = load_template("consent.html")
    html = (
        template.replace("{{client_name}}", client["client_name"])
        .replace("{{scope}}", scope)
        .replace("{{response_type}}", response_type)
        .replace("{{client_id}}", client_id)
        .replace("{{redirect_uri}}", redirect_uri)
        .replace("{{state}}", state)
        .replace("{{code_challenge}}", code_challenge)
        .replace("{{code_challenge_method}}", code_challenge_method)
    )
    return HTMLResponse(html)


async def authorize_post(request: Request) -> Response:
    """POST /oauth/authorize - Handle login or consent submission."""
    from backend.oauth.registration import get_client
    from backend.oauth.token import create_authorization_code

    form = await request.form()
    action = form.get("action")

    if action == "login":
        token = form.get("token")
        if not token:
            return HTMLResponse(
                "<html><body><h1>Error</h1><p>Token is required</p></body></html>",
                status_code=400,
            )

        # Validate against multiple sources
        valid = False

        # 1. Check MCP_AUTH_TOKEN env var
        mcp_token = os.environ.get("MCP_AUTH_TOKEN", "")
        if mcp_token and token == mcp_token:
            valid = True

        # 2. Check BEARER_TOKEN config
        if not valid:
            from backend.config import BEARER_TOKEN
            if BEARER_TOKEN and token == BEARER_TOKEN:
                valid = True

        # 3. Check against SQLite MCP token manager
        if not valid:
            from backend.mcp_token_manager import token_manager
            valid = token_manager.validate_token(token)

        if not valid:
            return HTMLResponse(
                "<html><body><h1>Error</h1><p>Invalid token</p></body></html>",
                status_code=401,
            )

        # Set session cookie and redirect back to authorize with same params
        auth_params = form.get("auth_params", "")
        response = RedirectResponse(
            url=f"/oauth/authorize?{auth_params}",
            status_code=303,
        )
        response.set_cookie(
            key="user_token",
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=3600,  # 1 hour session
        )
        return response

    elif action == "authorize":
        # User granted consent - generate authorization code
        response_type = form.get("response_type")
        client_id = form.get("client_id")
        redirect_uri = form.get("redirect_uri")
        scope = form.get("scope", "read")
        state = form.get("state", "")
        code_challenge = form.get("code_challenge")
        code_challenge_method = form.get("code_challenge_method")
        user_token = request.cookies.get("user_token")

        if not user_token:
            return HTMLResponse(
                "<html><body><h1>Error</h1><p>Not authenticated</p></body></html>",
                status_code=401,
            )

        # Validate client and redirect_uri
        client = get_client(client_id)
        is_localhost = redirect_uri and (redirect_uri.startswith("http://localhost:") or redirect_uri.startswith("http://127.0.0.1:"))
        if not client or (not is_localhost and redirect_uri not in client["redirect_uris"]):
            return HTMLResponse(
                "<html><body><h1>Error</h1><p>Invalid client or redirect_uri</p></body></html>",
                status_code=400,
            )

        # Generate authorization code
        auth_code = secrets.token_urlsafe(32)
        create_authorization_code(
            code=auth_code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            user_token=user_token,
            expires_in=600,  # 10 minutes
        )

        # Redirect back to client with authorization code
        parsed = urlparse(redirect_uri)
        params = {"code": auth_code}
        if state:
            params["state"] = state

        separator = "&" if parsed.query else "?"
        redirect_url = f"{redirect_uri}{separator}{urlencode(params)}"
        return RedirectResponse(url=redirect_url, status_code=303)

    elif action == "deny":
        redirect_uri = form.get("redirect_uri")
        state = form.get("state", "")
        parsed = urlparse(redirect_uri)
        params = {"error": "access_denied"}
        if state:
            params["state"] = state
        separator = "&" if parsed.query else "?"
        redirect_url = f"{redirect_uri}{separator}{urlencode(params)}"
        return RedirectResponse(url=redirect_url, status_code=303)

    return HTMLResponse(
        "<html><body><h1>Error</h1><p>Invalid action</p></body></html>",
        status_code=400,
    )


router = APIRouter()
router.add_api_route(
    "/oauth/authorize",
    authorize_get,
    methods=["GET"],
    include_in_schema=False,
)
router.add_api_route(
    "/oauth/authorize",
    authorize_post,
    methods=["POST"],
    include_in_schema=False,
)