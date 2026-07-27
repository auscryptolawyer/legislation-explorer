"""MCP server mounted inside the FastAPI app with dual transport (SSE + StreamableHTTP)."""
from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import anyio
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http import StreamableHTTPServerTransport
from mcp.types import TextContent, Tool
from starlette.requests import Request
from starlette.responses import Response


class NoopResponse(Response):
    """Response that does nothing when called — used after raw ASGI response is already sent."""
    async def __call__(self, scope, receive, send):
        pass

from backend.config import DATA_DIR
from backend.mcp_token_manager import token_manager
from backend.routes.api import VERSION, CHANGELOG
from backend.services.data_loader import (
    load_tree,
    get_rulings_for_section,
    get_commentary_for_section,
    get_definition_text,
)
from backend.services.search_service import search_sections as fts_search
from backend.routes.tax_cases import search_tax_cases
from backend.services.case_db_service import (
    build_download_urls,
    get_case_metadata,
    get_case_paragraphs,
    search_case_paragraphs as db_search_case_paragraphs,
)

logger = logging.getLogger(__name__)

sse_transport = SseServerTransport("/mcp/messages/")

mcp_server = Server("legislation-explorer")

# Track token per session — set when SSE connects, read when POST messages arrive
_session_tokens: dict[str, str] = {}


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_legislation",
            description="Search legislation sections by keyword or section number. All query terms must appear in section text (AND matching). Note: colloquial names like 'Division 7A' won't match literally in legislation body text — use specific section numbers or keywords for best results.",
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
            description="List all available acts and ATO rulings",
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
            description="Look up the definition of a term in an act. Returns the full definition text, not just a locator.",
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
            name="search_cases",
            description="Search tax cases by name, citation, or catchwords. Returns flat list with weblinks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query - case name, citation, or catchwords"},
                    "limit": {"type": "integer", "description": "Max results (default 20, max 100)", "default": 20},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_info",
            description="Return server version, changelog, and list of all available MCP tools and REST endpoints.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_ruling",
            description="Retrieve an ATO ruling by citation. Accepts TR 2020/1, TR_2020_1, or TR 2024/1 formats.",
            inputSchema={
                "type": "object",
                "properties": {
                    "citation": {"type": "string", "description": "Ruling citation (e.g. TR 2020/1, TR_2020_1, TR 2024/1)"},
                },
                "required": ["citation"],
            },
        ),
        Tool(
            name="get_case",
            description="Get case metadata and structural outline. No paragraph text returned. Use get_case_paragraphs to read paragraphs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "citation": {"type": "string", "description": "Case citation (e.g. [2024] HCA 1)"},
                    "include_legislation_refs": {"type": "boolean", "description": "Include legislation references", "default": False},
                },
                "required": ["citation"],
            },
        ),
        Tool(
            name="list_rulings",
            description="List all ATO rulings grouped by year and type. Returns the full ruling tree with ATO.gov.au and AustLII links.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_case_paragraphs",
            description="Retrieve paragraphs from a case, filtered by section type and/or sequence range. Use get_case first to see available section types. At least one filter required.",
            inputSchema={
                "type": "object",
                "properties": {
                    "citation": {"type": "string", "description": "Case citation (e.g. [2024] HCA 1)"},
                    "section_types": {"type": "array", "items": {"type": "string"}, "description": "Filter by section types (e.g. FACTS, REASONING)"},
                    "paragraph_start": {"type": "integer", "description": "Offset within filtered results", "default": 0},
                    "paragraph_limit": {"type": "integer", "description": "Max paragraphs (default 50, max 100)", "default": 50},
                    "range_start": {"type": "integer", "description": "Start of sequence order range"},
                    "range_end": {"type": "integer", "description": "End of sequence order range"},
                },
                "required": ["citation"],
            },
        ),
        Tool(
            name="search_case_paragraphs",
            description="Full-text search across case paragraphs. Uses exact-phrase matching (not keyword AND) — omit stopwords that may not appear verbatim. If citation is omitted, searches ALL cases. Returns snippets.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "citation": {"type": "string", "description": "Optional case citation to scope search"},
                    "section_types": {"type": "array", "items": {"type": "string"}, "description": "Filter by section types"},
                    "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="download_case",
            description="Get download links for full case text. Use these URLs to download the full case from AustLII or court website for offline research. MCP does not serve full text directly.",
            inputSchema={
                "type": "object",
                "properties": {
                    "citation": {"type": "string", "description": "Case citation (e.g. [2024] HCA 1)"},
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
        elif name == "get_rulings_for_section":
            return await _get_rulings_for_section(arguments)
        elif name == "get_ruling":
            return await _get_ruling(arguments)
        elif name == "search_cases":
            return await _search_cases(arguments)
        elif name == "get_info":
            return await _get_info(arguments)
        elif name == "get_case":
            return await _get_case(arguments)
        elif name == "list_rulings":
            return await _list_rulings(arguments)
        elif name == "get_case_paragraphs":
            return await _get_case_paragraphs(arguments)
        elif name == "search_case_paragraphs":
            return await _search_case_paragraphs(arguments)
        elif name == "download_case":
            return await _download_case(arguments)
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
    acts.append({"id": "rulings", "name": "ATO Rulings"})
    return [TextContent(type="text", text=json.dumps({"acts": acts}, indent=2))]


async def _get_act_tree(args: dict) -> list[TextContent]:
    act = args["act"]
    tree = load_tree(act)
    return [TextContent(type="text", text=json.dumps(tree, indent=2))]


async def _get_definition(args: dict) -> list[TextContent]:
    """Return definition text for a term in an act."""
    act = args["act"]
    term = args["term"]
    result = get_definition_text(act, term)
    if result:
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    return [TextContent(type="text", text=json.dumps({"error": f"Definition for '{term}' not found in {act}"}))]


async def _get_rulings_for_section(args: dict) -> list[TextContent]:
    from backend.services.data_loader import load_rulings
    rulings = get_rulings_for_section(args["act"], args["section"], limit=50, offset=0)
    ruling_list = load_rulings()
    richer = []
    for r in rulings:
        found = next((item for item in ruling_list if item["citation"] == r["citation"]), None)
        if found:
            richer.append(found)
        else:
            richer.append(r)
    return [TextContent(type="text", text=json.dumps({"rulings": richer}, indent=2))]


async def _get_info(_args: dict) -> list[TextContent]:
    """Return server version, changelog, and tool list."""
    mcp_tools = [
        "search_legislation", "get_section", "list_acts", "get_act_tree",
        "get_definition", "get_rulings_for_section", "search_cases",
        "get_info", "get_ruling", "get_case", "get_case_paragraphs",
        "search_case_paragraphs", "download_case", "list_rulings",
    ]
    return [TextContent(type="text", text=json.dumps({
        "name": "Legislation Explorer",
        "version": VERSION,
        "mcp_tools": mcp_tools,
        "mcp_tool_count": len(mcp_tools),
        "changelog": CHANGELOG,
    }, indent=2))]


async def _search_cases(args: dict) -> list[TextContent]:
    """Search tax cases by name, citation, or catchwords."""
    query = args.get("query", "").strip()
    limit = min(100, max(1, args.get("limit", 20)))
    result = search_tax_cases(q=query, limit=limit)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _get_ruling(args: dict) -> list[TextContent]:
    import json as _json
    import re as _re
    from pathlib import Path
    from backend.services.data_loader import load_rulings
    citation = args["citation"]
    # Citation alias: LCR → LCG
    CITATION_ALIASES = {"LCR": "LCG"}
    # Normalize: "TR 2020/1" → "TR_2020_1"
    normalized = _re.sub(r'[\s/]+', '_', citation).strip('_')
    candidates = {normalized}
    prefix_m = _re.match(r'^([A-Za-z]+)_(.*)$', normalized)
    if prefix_m and prefix_m.group(1).upper() in CITATION_ALIASES:
        candidates.add(f"{CITATION_ALIASES[prefix_m.group(1).upper()]}_{prefix_m.group(2)}")
    for r in load_rulings():
        if r["citation"] in candidates:
            path = Path(r["source"])
            content = path.read_text(encoding="utf-8") if path.exists() else ""
            return [TextContent(type="text", text=_json.dumps({
                "citation": r["citation"],
                "citation_display": r.get("citation_display", ""),
                "title": r["title"],
                "full_title": r.get("full_title", ""),
                "type": r["type"],
                "year": r["year"],
                "ato_url": r.get("ato_url", ""),
                "austlii_url": r.get("austlii_url", ""),
                "content": content,
            }, indent=2))]
    return [TextContent(type="text", text=_json.dumps({"error": f"Ruling {citation} not found"}))]


async def _list_rulings(_args: dict) -> list[TextContent]:
    """Return the full rulings tree grouped by year and type."""
    import json as _json
    from backend.services.data_loader import load_rulings
    rulings = load_rulings()
    # Group by year, then type
    years: dict = {}
    for r in rulings:
        year = r.get("year", 0)
        t = r.get("type", "Ruling")
        if year not in years:
            years[year] = {}
        if t not in years[year]:
            years[year][t] = []
        years[year][t].append({
            "citation": r["citation"],
            "citation_display": r.get("citation_display", ""),
            "title": r.get("full_title", r.get("title", "")),
            "ato_url": r.get("ato_url", ""),
            "austlii_url": r.get("austlii_url", ""),
        })
    return [TextContent(type="text", text=_json.dumps({"ato_rulings_total": len(rulings), "by_year": years}, indent=2))]


async def _get_case(args: dict) -> list[TextContent]:
    """Get case metadata and structural outline."""
    import re
    citation = args["citation"]
    # Strip party names if full citation is provided (e.g. "Bywater Investments Ltd v Commissioner of Taxation [2016] HCA 45")
    # Extract the bare neutral citation in brackets
    m = re.search(r'\[(\d{4})\]?\s*([A-Z]+(?:\s*[A-Z]+)*)\s*(\d+)', citation)
    if m:
        bare = f"[{m.group(1)}] {m.group(2)} {m.group(3)}"
        citation = bare
    include_legislation_refs = args.get("include_legislation_refs", False)
    result = get_case_metadata(citation, include_legislation_refs=include_legislation_refs)
    if result is None:
        return [TextContent(type="text", text=json.dumps({"error": f"Case {args['citation']} not found. Try the bare neutral citation format, e.g. [2016] HCA 45"}))]
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _get_case_paragraphs(args: dict) -> list[TextContent]:
    """Retrieve paragraphs from a case."""
    citation = args["citation"]
    section_types = args.get("section_types")
    paragraph_start = args.get("paragraph_start", 0)
    paragraph_limit = args.get("paragraph_limit", 50)
    range_start = args.get("range_start")
    range_end = args.get("range_end")
    result = get_case_paragraphs(
        citation,
        section_types=section_types,
        paragraph_start=paragraph_start,
        paragraph_limit=paragraph_limit,
        range_start=range_start,
        range_end=range_end,
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _search_case_paragraphs(args: dict) -> list[TextContent]:
    """Full-text search across case paragraphs."""
    query = args["query"]
    citation = args.get("citation")
    section_types = args.get("section_types")
    limit = args.get("limit", 10)
    result = db_search_case_paragraphs(
        query,
        citation=citation,
        section_types=section_types,
        limit=limit,
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _download_case(args: dict) -> list[TextContent]:
    """Get download links for full case text."""
    citation = args["citation"]
    result = build_download_urls(citation)
    if result is None:
        return [TextContent(type="text", text=json.dumps({"error": f"Could not parse or find case: {citation}"}))]
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ---------------------------------------------------------------------------
# SSE handlers with auth + rate limiting + session-bound tokens
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
        # The session_id was just added to _read_stream_writers by connect_sse.
        # Dicts preserve insertion order, so the last key is the current session.
        session_ids = list(sse_transport._read_stream_writers.keys())
        session_hex = session_ids[-1].hex if session_ids else ""
        _session_tokens[session_hex] = token
        try:
            await mcp_server.run(
                streams[0], streams[1], mcp_server.create_initialization_options()
            )
        finally:
            _session_tokens.pop(session_hex, None)
    return NoopResponse()


async def mcp_post_message_app(scope, receive, send):
    """ASGI app for MCP POST messages with auth via session-bound token."""
    request = Request(scope, receive)
    token = request.query_params.get("token", "")
    session_id = request.query_params.get("session_id", "")

    if not token and session_id:
        token = _session_tokens.get(session_id, "")

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


# ---------------------------------------------------------------------------
# Streamable HTTP handler
# ---------------------------------------------------------------------------


async def handle_mcp_streamable(request: Request):
    """Handle Streamable HTTP MCP requests with auth + rate limiting.

    Supports dual-mode auth: JWT (OAuth 2.1) or legacy raw token.
    Uses stateless pattern: creates a fresh transport per request.
    """
    import os
    from jose import JWTError, jwt as jose_jwt

    # Extract token from Authorization header or query param
    token = ""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        token = request.query_params.get("token", "")

    if not token:
        return Response("Missing token", status_code=401)

    # Try JWT validation first (OAuth 2.1 flow)
    jwt_valid = False
    jwt_secret = os.environ.get("JWT_SECRET", "")
    if jwt_secret:
        try:
            payload = jose_jwt.decode(
                token, jwt_secret, algorithms=["HS256"],
                options={"verify_exp": True, "verify_aud": False},
            )
            # Check revocation in OAuth tokens DB
            import hashlib
            import sqlite3 as _sqlite3
            from backend.oauth.token import DB_PATH as OAUTH_DB_PATH

            token_hash = hashlib.sha256(token.encode()).hexdigest()
            conn = _sqlite3.connect(str(OAUTH_DB_PATH))
            try:
                row = conn.execute(
                    "SELECT revoked FROM oauth_access_tokens WHERE token_hash = ?",
                    (token_hash,),
                ).fetchone()
                if row and row[0]:
                    return Response("Token revoked", status_code=403)
            finally:
                conn.close()
            jwt_valid = True
        except (JWTError, Exception):
            jwt_valid = False

    # Fall back to legacy token manager
    if not jwt_valid:
        if not token_manager.validate_token(token):
            return Response("Invalid or revoked token", status_code=403)

    # Rate limiting (always use raw token for rate limiting)
    allowed, reason = token_manager.check_rate_limit(token)
    if not allowed:
        return Response(reason, status_code=429)

    # Create a fresh transport for this request (stateless)
    transport = StreamableHTTPServerTransport(
        mcp_session_id=None,
        is_json_response_enabled=True,
    )

    async def run_mcp_server(*, task_status=anyio.TASK_STATUS_IGNORED):
        async with transport.connect() as streams:
            read_stream, write_stream = streams
            task_status.started()
            try:
                await mcp_server.run(
                    read_stream,
                    write_stream,
                    mcp_server.create_initialization_options(),
                    stateless=True,
                )
            except Exception:
                logger.exception("StreamableHTTP session crashed")

    async with anyio.create_task_group() as tg:
        await tg.start(run_mcp_server)
        await transport.handle_request(
            request.scope, request.receive, request._send
        )

    await transport.terminate()
    return NoopResponse()
