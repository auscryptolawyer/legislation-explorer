"""API routes for MCP token management."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.mcp_token_manager import token_manager

router = APIRouter()


class CreateTokenRequest(BaseModel):
    name: str = ""


class RenameTokenRequest(BaseModel):
    name: str


def _get_user(request: Request) -> dict | None:
    """Try to get authenticated user. Returns None if not authenticated or auth not configured."""
    try:
        from backend.auth import require_user
        return require_user(request)
    except Exception:
        return None


def _user_email(request: Request) -> str:
    """Get the current user's email for token filtering. Returns '' if not auth'd."""
    user = _get_user(request)
    if user:
        return user.get("email") or user.get("name", "")
    return ""


@router.post("/api/mcp-token")
def create_mcp_token(request: Request, body: CreateTokenRequest):
    """Create a new named MCP access token. Requires authentication."""
    user = _get_user(request)
    if not user:
        return JSONResponse({"error": "Login required to create MCP tokens"}, status_code=401)
    created_by = user.get("email") or user.get("name", "")
    token = token_manager.create_token(name=body.name, created_by=created_by)
    return {"token": token, "message": "Copy this token now — it will not be shown again."}


@router.get("/api/mcp-hall-of-fame")
def mcp_hall_of_fame():
    """Leaderboard of MCP call counts by token name, over all-time/monthly/daily windows."""
    return token_manager.hall_of_fame()


@router.get("/api/mcp-tokens")
def list_mcp_tokens(request: Request):
    """List active MCP tokens for the current user. Requires authentication."""
    user = _get_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    email = user.get("email") or user.get("name", "")
    tokens = token_manager.list_tokens(created_by=email)
    return {"tokens": tokens}


@router.post("/api/mcp-tokens/{token_id}/revoke")
def revoke_mcp_token(token_id: str, request: Request) -> JSONResponse:
    """Revoke an MCP token. Requires authentication."""
    user = _get_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    revoked = token_manager.revoke_token(token_id)
    if revoked:
        return JSONResponse({"message": "Token revoked"})
    return JSONResponse({"error": "Token not found or already revoked"}, status_code=404)


@router.post("/api/mcp-tokens/{token_id}/rename")
def rename_mcp_token(token_id: str, body: RenameTokenRequest, request: Request) -> JSONResponse:
    """Rename an MCP token. Requires authentication."""
    user = _get_user(request)
    if not user:
        return JSONResponse({"error": "Login required"}, status_code=401)
    renamed = token_manager.rename_token(token_id, body.name)
    if renamed:
        return JSONResponse({"message": "Token renamed"})
    return JSONResponse({"error": "Token not found"}, status_code=404)
