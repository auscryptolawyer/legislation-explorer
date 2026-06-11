"""MCP server mounted inside the FastAPI app."""
from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool
from starlette.requests import Request
from starlette.responses import Response


class NoopResponse(Response):
    """Response that does nothing when called — used after raw ASGI response is already sent."""
    async def __call__(self, scope, receive, send):
        pass

from backend.config import DATA_DIR
from backend.mcp_token_manager import token_manager
from backend.services.data_loader import (
    load_tree,
    load_definitions,
    get_cases_for_section,
    get_rulings_for_section,
    get_commentary_for_section,
)
from backend.services.search_service import search_sections as fts_search

logger = logging.getLogger(__name__)

sse_transport = SseServerTransport("/mcp/messages/")

mcp_server = Server("legislation-explorer")


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_legislation",
            description="Search legislation sections by keyword or section number",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query or section number"},
                    "act": {"type": "string", "description": "Optional act ID to restrict search (e.g. itaa-1997)"},
                    "limit": {"type": "integer", "description": "Max results (default 20, max 100)", "default": 20},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_section",
            description="Retrieve full text of a legislation section",
            inputSchema={
                "type": "object",
                "properties": {
                    "act": {"type": "string", "description": "Act ID (e.g. itaa-1997)"},
                    "section": {"type": "string", "description": "Section number (e.g. 8-1)"},
                },
                "required": ["act", "section"],
            },
        ),
        Tool(
            name="list_acts",
            description="List all available acts",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_act_tree",
            description="Get the full structure of an act (parts, divisions, sections)",
            inputSchema={
                "type": "object",
                "properties": {
                    "act": {"type": "string", "description": "Act ID (e.g. itaa-1997)"},
                },
                "required": ["act"],
            },
        ),
        Tool(
            name="get_definition",
            description="Look up the definition of a term in an act",
            inputSchema={
                "type": "object",
                "properties": {
                    "act": {"type": "string", "description": "Act ID"},
                    "term": {"type": "string", "description": "Term to define"},
                },
                "required": ["act", "term"],
            },
        ),
        Tool(
            name="get_cases_for_section",
            description="Get cases related to a legislation section",
            inputSchema={
                "type": "object",
                "properties": {
                    "act": {"type": "string", "description": "Act ID"},
                    "section": {"type": "string", "description": "Section number"},
                },
                "required": ["act", "section"],
            },
        ),
        Tool(
            name="get_rulings_for_section",
            description="Get ATO rulings related to a legislation section",
            inputSchema={
                "type": "object",
                "properties": {
                    "act": {"type": "string", "description": "Act ID"},
                    "section": {"type": "string", "description": "Section number"},
                },
                "required": ["act", "section"],
            },
        ),
        Tool(
            name="get_case",
            description="Retrieve a case by citation",
            inputSchema={
                "type": "object",
                "properties": {
                    "citation": {"type": "string", "description": "Case citation (e.g. [2022] HCA 10)"},
                },
                "required": ["citation"],
            },
        ),
        Tool(
            name="get_ruling",
            description="Retrieve an ATO ruling by citation",
            inputSchema={
                "type": "object",
                "properties": {
                    "citation": {"type": "string", "description": "Ruling citation (e.g. TR 2024/1)"},
                },
                "required": ["citation"],
            },
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    logger.info(f"MCP tool call: {name}({arguments})")
    try:
        if name == "search_legislation":
            return await _search_legislation(arguments)
        elif name == "get_section":
            return await _get_section(arguments)
        elif name == "list_acts":
            return await _list_acts(arguments)
        elif name == "get_act_tree":
            return await _get_act_tree(arguments)
        elif name == "get_definition":
            return await _get_definition(arguments)
        elif name == "get_cases_for_section":
            return await _get_cases_for_section(arguments)
        elif name == "get_rulings_for_section":
            return await _get_rulings_for_section(arguments)
        elif name == "get_case":
            return await _get_case(arguments)
        elif name == "get_ruling":
            return await _get_ruling(arguments)
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
    except Exception as e:
        logger.exception(f"MCP tool error: {name}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def _search_legislation(args: dict) -> list[TextContent]:
    q = args.get("query", "").strip()
    act = args.get("act")
    limit = min(100, max(1, args.get("limit", 20)))
    results = fts_search(q, act, limit=limit)
    payload = {
        "query": q,
        "total": len(results),
        "results": results,
    }
    return [TextContent(type="text", text=json.dumps(payload, indent=2))]


async def _get_section(args: dict) -> list[TextContent]:
    act = args["act"]
    section = args["section"]
    tree = load_tree(act)
    section_path = None
    for part in tree.get("parts", []):
        for sec in part.get("sections", []):
            if sec["id"] == section:
                section_path = sec["path"]
                break
        if section_path:
            break
        for div in part.get("divisions", []):
            for sec in div.get("sections", []):
                if sec["id"] == section:
                    section_path = sec["path"]
                    break
            if not section_path:
                for sub in div.get("subdivisions", []):
                    for sec in sub.get("sections", []):
                        if sec["id"] == section:
                            section_path = sec["path"]
                            break
            if section_path:
                break
        if section_path:
            break

    if not section_path:
        for md in (DATA_DIR / act / "sections").rglob(f"{section}.md"):
            section_path = str(md.relative_to(DATA_DIR / act / "sections"))
            break

    if not section_path:
        return [TextContent(type="text", text=json.dumps({"error": f"Section {section} not found"}))]

    md_path = DATA_DIR / act / "sections" / section_path
    if not md_path.exists():
        return [TextContent(type="text", text=json.dumps({"error": "Section file not found"}))]

    content = md_path.read_text(encoding="utf-8")
    # Strip frontmatter
    body = content
    if content.startswith("---"):
        import re
        fm_end = re.search(r'\n---\s*\n', content)
        if fm_end:
            body = content[fm_end.end():]

    return [TextContent(type="text", text=json.dumps({
        "act": act,
        "section": section,
        "body": body,
    }, indent=2))]


async def _list_acts(_args: dict) -> list[TextContent]:
    acts = []
    for act_dir in sorted(DATA_DIR.iterdir()):
        if act_dir.is_dir() and (act_dir / "tree.json").exists():
            tree = load_tree(act_dir.name)
            acts.append({
                "id": act_dir.name,
                "name": tree.get("act", act_dir.name),
                "compilation_no": tree.get("compilation_no"),
                "compilation_date": tree.get("compilation_date"),
            })
    acts.append({"id": "cases", "name": "Cases"})
    acts.append({"id": "rulings", "name": "ATO Rulings"})
    return [TextContent(type="text", text=json.dumps({"acts": acts}, indent=2))]


async def _get_act_tree(args: dict) -> list[TextContent]:
    act = args["act"]
    tree = load_tree(act)
    return [TextContent(type="text", text=json.dumps(tree, indent=2))]


async def _get_definition(args: dict) -> list[TextContent]:
    act = args["act"]
    term = args["term"]
    defs = load_definitions(act)
    key = term.lower()
    if key in defs:
        return [TextContent(type="text", text=json.dumps(defs[key], indent=2))]
    import re
    slug = re.sub(r"[^a-z0-9\s-]", "", key).strip()
    slug = re.sub(r"\s+", "-", slug)
    for k, v in defs.items():
        if v.get("anchor") == f"s995-1-{slug}" or v.get("anchor") == f"s6-{slug}":
            return [TextContent(type="text", text=json.dumps(v, indent=2))]
    return [TextContent(type="text", text=json.dumps({"error": f"Definition for '{term}' not found"}))]


async def _get_cases_for_section(args: dict) -> list[TextContent]:
    cases = get_cases_for_section(args["act"], args["section"], limit=50, offset=0)
    return [TextContent(type="text", text=json.dumps({"cases": cases}, indent=2))]


async def _get_rulings_for_section(args: dict) -> list[TextContent]:
    rulings = get_rulings_for_section(args["act"], args["section"], limit=50, offset=0)
    return [TextContent(type="text", text=json.dumps({"rulings": rulings}, indent=2))]


async def _get_case(args: dict) -> list[TextContent]:
    import json as _json
    from backend.config import CASE_DIR
    from backend.services.data_loader import short_case_name
    citation = args["citation"]
    for f in CASE_DIR.glob("*.json"):
        try:
            data = _json.loads(f.read_text(encoding="utf-8"))
            if data.get("citation") == citation:
                return [TextContent(type="text", text=_json.dumps({
                    "citation": data.get("citation"),
                    "case_name": data.get("case_name"),
                    "court": data.get("court"),
                    "year": data.get("year"),
                    "decision_date": data.get("decision_date"),
                    "content": data.get("content"),
                    "short_name": short_case_name(data.get("case_name", "")),
                }, indent=2))]
        except Exception:
            pass
    return [TextContent(type="text", text=_json.dumps({"error": f"Case {citation} not found"}))]


async def _get_ruling(args: dict) -> list[TextContent]:
    import json as _json
    from pathlib import Path
    from backend.services.data_loader import load_rulings
    citation = args["citation"]
    for r in load_rulings():
        if r["citation"] == citation:
            path = Path(r["source"])
            content = path.read_text(encoding="utf-8") if path.exists() else ""
            return [TextContent(type="text", text=_json.dumps({
                "citation": r["citation"],
                "title": r["title"],
                "type": r["type"],
                "year": r["year"],
                "content": content,
            }, indent=2))]
    return [TextContent(type="text", text=_json.dumps({"error": f"Ruling {citation} not found"}))]


# ---------------------------------------------------------------------------
# SSE handlers with auth + rate limiting
# ---------------------------------------------------------------------------

async def handle_mcp_sse(request: Request):
    """Handle SSE connection for MCP with auth + rate limiting."""
    token = request.query_params.get("token", "")
    if not token:
        return Response("Missing token", status_code=401)
    if not token_manager.validate_token(token):
        return Response("Invalid or revoked token", status_code=403)
    allowed, reason = token_manager.check_rate_limit(token)
    if not allowed:
        return Response(reason, status_code=429)

    scope = request.scope
    receive = request.receive
    send = request._send

    async with sse_transport.connect_sse(scope, receive, send) as streams:
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )
    return NoopResponse()


async def mcp_post_message_app(scope, receive, send):
    """ASGI app for MCP POST messages with auth + rate limiting."""
    request = Request(scope, receive)
    token = request.query_params.get("token", "")
    if not token:
        response = Response("Missing token", status_code=401)
        return await response(scope, receive, send)
    if not token_manager.validate_token(token):
        response = Response("Invalid or revoked token", status_code=403)
        return await response(scope, receive, send)
    allowed, reason = token_manager.check_rate_limit(token)
    if not allowed:
        response = Response(reason, status_code=429)
        return await response(scope, receive, send)
    await sse_transport.handle_post_message(scope, receive, send)
