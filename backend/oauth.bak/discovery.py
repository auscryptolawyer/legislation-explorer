"""OAuth 2.1 Authorization Server Metadata (RFC 8414) and Protected Resource Metadata (RFC 9728)."""

import os

from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import JSONResponse


def _get_base_url(request: Request) -> str:
    """Get base URL from environment or request."""
    return os.environ.get("OAUTH_ISSUER") or str(request.base_url).rstrip("/")


async def oauth_metadata(request: Request) -> JSONResponse:
    """Return OAuth 2.1 authorization server metadata.

    Implements RFC 8414 - OAuth 2.0 Authorization Server Metadata.
    """
    base_url = _get_base_url(request)

    metadata = {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "registration_endpoint": f"{base_url}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic",
            "none",
        ],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": ["read", "write"],
        "require_request_uri_registration": True,
        "require_pkce": True,
    }

    return JSONResponse(metadata)


async def protected_resource_metadata(request: Request) -> JSONResponse:
    """Return OAuth 2.0 Protected Resource Metadata.

    Implements RFC 9728 - OAuth 2.0 Protected Resource Metadata.
    Claude MCP clients check this first to discover the authorization server.
    """
    base_url = _get_base_url(request)

    metadata = {
        "resource": base_url,
        "authorization_servers": [base_url],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["read", "write"],
        "resource_documentation": f"{base_url}/docs",
    }

    return JSONResponse(metadata)


router = APIRouter()
router.add_api_route(
    "/.well-known/oauth-authorization-server",
    oauth_metadata,
    methods=["GET"],
    include_in_schema=False,
)
router.add_api_route(
    "/.well-known/oauth-protected-resource",
    protected_resource_metadata,
    methods=["GET"],
    include_in_schema=False,
)