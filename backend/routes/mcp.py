"""API routes for MCP token management."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.mcp_token_manager import token_manager

router = APIRouter()


class CreateTokenRequest(BaseModel):
    name: str = ""


@router.post("/api/mcp-token")
def create_mcp_token(body: CreateTokenRequest):
    """Create a new named MCP access token."""
    token = token_manager.create_token(body.name)
    return {"token": token, "message": "Copy this token now — it will not be shown again."}


@router.get("/api/mcp-hall-of-fame")
def mcp_hall_of_fame():
    """Leaderboard of MCP call counts by token name, over all-time/monthly/daily windows."""
    return token_manager.hall_of_fame()


@router.get("/api/mcp-tokens")
def list_mcp_tokens():
    """List active MCP tokens (without raw tokens)."""
    return {"tokens": token_manager.list_tokens()}


@router.post("/api/mcp-tokens/{token}/revoke")
def revoke_mcp_token(token: str) -> JSONResponse:
    """Revoke an MCP token."""
    revoked = token_manager.revoke_token(token)
    if revoked:
        return JSONResponse({"message": "Token revoked"})
    return JSONResponse({"error": "Token not found or already revoked"}, status_code=404)
