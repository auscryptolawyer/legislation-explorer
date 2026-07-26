"""Admin-only routes: token dashboard, system health, re-index, logs, users."""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.mcp_token_manager import token_manager
from backend.services.login_log import get_users

router = APIRouter()

ADMIN_EMAIL = "harrison.dell@cadenalegal.com.au"

# Server start time for uptime calculation
_SERVER_START = time.time()


def _require_admin(request: Request) -> dict:
    """Gate admin routes to Harry's account only."""
    try:
        from backend.auth import require_user
        user = require_user(request)
    except Exception:
        raise HTTPException(401, "Login required")
    if user.get("email") != ADMIN_EMAIL:
        raise HTTPException(403, "Admin access required")
    return user


@router.get("/api/admin/tokens")
def admin_list_tokens(request: Request):
    _require_admin(request)
    tokens = token_manager.list_tokens()
    return {"tokens": tokens}


@router.post("/api/admin/tokens/{token_id}/revoke")
def admin_revoke_token(token_id: str, request: Request):
    _require_admin(request)
    revoked = token_manager.revoke_token(token_id)
    if revoked:
        return JSONResponse({"message": "Token revoked"})
    return JSONResponse({"error": "Token not found"}, status_code=404)


@router.get("/api/admin/health")
def admin_health(request: Request):
    _require_admin(request)

    uptime = time.time() - _SERVER_START

    # DB row counts (PostgreSQL via docker exec)
    db_stats = {}
    try:
        r = subprocess.run(
            ["docker", "exec", "cadena-postgres", "psql", "-U", "cadena", "-d", "cadena_knowledge", "-t", "-A",
             "-c", "SELECT (SELECT COUNT(*) FROM cases) as cases, (SELECT COUNT(*) FROM case_paragraphs) as case_paras, (SELECT COUNT(*) FROM rulings) as rulings"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and r.stdout.strip():
            parts = r.stdout.strip().split("|")
            if len(parts) >= 3:
                db_stats["cases"] = int(parts[0])
                db_stats["case_paragraphs"] = int(parts[1])
                db_stats["rulings"] = int(parts[2])
    except Exception:
        db_stats["error"] = "Could not query PostgreSQL"

    # MCP tokens count
    mcp_tokens_count = len(token_manager.list_tokens())

    # Last backup
    backup_dir = Path("/home/harrison/legislation-explorer/data")
    backups = sorted(backup_dir.glob("cadena_db_backup_*.sql.gz"), key=lambda f: f.stat().st_mtime, reverse=True)
    last_backup = backups[0].stat().st_mtime if backups else None

    # Search index
    search_db = Path("/home/harrison/legislation-explorer/search_index.db")
    search_index_built = search_db.stat().st_mtime if search_db.exists() else None

    # Legislation compile info
    legislation = []
    try:
        from backend.config import DATA_DIR
        for act_dir in sorted(DATA_DIR.iterdir()):
            if act_dir.is_dir() and (act_dir / "tree.json").exists():
                import json as _json
                tree = _json.loads((act_dir / "tree.json").read_text())
                legislation.append({
                    "act": act_dir.name,
                    "name": tree.get("act", act_dir.name),
                    "compilation_no": tree.get("compilation_no"),
                    "compilation_date": tree.get("compilation_date"),
                })
    except Exception:
        pass

    return {
        "backend": {
            "uptime_seconds": round(uptime),
            "version": "2.3.1",
            "auth_enabled": bool(os.environ.get("AZURE_CLIENT_ID")),
        },
        "database": {
            **db_stats,
            "mcp_tokens": mcp_tokens_count,
            "last_backup": last_backup,
            "search_index_built": search_index_built,
        },
        "legislation": legislation,
    }


@router.post("/api/admin/reindex")
def admin_reindex(request: Request):
    _require_admin(request)
    # Run reindex in background
    import threading
    def _reindex():
        try:
            from backend.services.search_service import init_search_index
            init_search_index()
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("Reindex failed")
    threading.Thread(target=_reindex, daemon=True).start()
    return {"status": "started", "message": "Reindexing in background. Check health endpoint for updated search_index_built."}


@router.get("/api/admin/logs")
def admin_logs(request: Request, lines: int = 50, level: str = ""):
    _require_admin(request)
    lines = min(200, max(10, lines))
    try:
        cmd = ["journalctl", "--user", "-u", "legislation-explorer", "--no-pager", "-n", str(lines),
               "-o", "short-iso"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        log_lines = r.stdout.strip().split("\n") if r.stdout.strip() else []
        if level:
            log_lines = [l for l in log_lines if level.upper() in l.upper()]
        return {"logs": log_lines[-lines:], "total": len(log_lines)}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/admin/users")
def admin_users(request: Request):
    _require_admin(request)
    users = get_users()
    return {"users": users}