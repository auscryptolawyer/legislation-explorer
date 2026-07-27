"""backend/main.py — FastAPI app for Legislation Explorer.

Serves:
  - React SPA static files
  - JSON API for tree, sections, definitions, search
  - Microsoft Entra ID SSO authentication
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.config import ALLOWED_ORIGINS, BEARER_TOKEN, FRONTEND_DIST, SEARCH_DB
from backend import config
from backend.logging_config import setup_logging
from backend.middleware.metrics import MetricsMiddleware
from backend.middleware.ratelimit import RateLimitMiddleware
from backend.routes.api import router as api_router
from backend.routes.mcp import router as mcp_router
from backend.mcp_server import handle_mcp_sse, mcp_post_message_app
from backend.services.search_service import init_search_index
from backend.services import vector_search_service

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build search index in background on startup if missing or stale."""
    if not SEARCH_DB.exists():
        logger.info("Search index missing, building in background...")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, init_search_index)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, vector_search_service.load)
    yield


app = FastAPI(title="Legislation Explorer", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Metrics
app.add_middleware(MetricsMiddleware)

# Rate limiting (on by default, disable with RATE_LIMIT_ENABLED=false)
app.add_middleware(RateLimitMiddleware, enabled=os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true")

# ---------------------------------------------------------------------------
# Microsoft Entra ID SSO auth
# ---------------------------------------------------------------------------

if os.environ.get("AZURE_CLIENT_ID"):
    from starlette.middleware.sessions import SessionMiddleware
    from backend.auth import AuthMiddleware, login, callback, logout, me

    app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "change-me"), session_cookie="starlette_session")
    app.add_middleware(AuthMiddleware)

    app.add_api_route("/auth/login", login, methods=["GET"])
    app.add_api_route("/auth/callback", callback, methods=["GET"])
    app.add_api_route("/auth/logout", logout, methods=["GET"])
    app.add_api_route("/auth/me", me, methods=["GET"])
    logger.info("Microsoft Entra ID auth enabled")

# ---------------------------------------------------------------------------
# Fallback: bearer token auth (when SSO is not configured)
# ---------------------------------------------------------------------------

if not os.environ.get("AZURE_CLIENT_ID"):

    @app.middleware("http")
    async def bearer_auth_middleware(request: Request, call_next):
        path = request.url.path
        if path in ("/health", "/", "/favicon.ico") or path.startswith(("/assets/", "/mcp/", "/auth/")):
            return await call_next(request)
        if not path.startswith("/api/"):
            return await call_next(request)
        if config.BEARER_TOKEN is None:
            return await call_next(request)
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] != config.BEARER_TOKEN:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

app.include_router(api_router)
app.include_router(mcp_router)


# ---------------------------------------------------------------------------
# MCP SSE transport (raw ASGI)
# ---------------------------------------------------------------------------

from starlette.routing import Route, Mount

app.routes.insert(
    0,
    Route("/mcp/sse", endpoint=handle_mcp_sse, methods=["GET"]),
)
app.routes.insert(
    1,
    Mount("/mcp/messages/", app=mcp_post_message_app),
)


# ---------------------------------------------------------------------------
# Static files / SPA fallback
# ---------------------------------------------------------------------------

from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if SCRIPTS_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(SCRIPTS_DIR)), name="static")

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index, headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            })
        return HTMLResponse("<h1>Legislation Explorer</h1><p>Frontend not built yet.</p>")
