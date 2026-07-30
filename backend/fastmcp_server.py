"""FastMCP server for Legislation Explorer — replaces old mcp_server.py.

Mount via streamable_http_app() on the main FastAPI app.
"""
from __future__ import annotations

import json
import logging
import os
import re as _re
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from backend.config import DATA_DIR
from backend.mcp_token_manager import token_manager
from backend.routes.api import VERSION, CHANGELOG
from backend.services.data_loader import (
    load_tree,
    load_rulings,
    get_definition_text,
)
from backend.services.search_service import search_sections as fts_search
from backend.routes.tax_cases import search_tax_cases
from backend.services.case_db_service import (
    build_download_urls,
    get_case_metadata,
    get_case_references,
)

logger = logging.getLogger(__name__)

# Public hostnames that hit this server via Cloudflare Tunnel / Caddy.
# FastMCP auto-enables DNS-rebinding protection for localhost host defaults and
# only allows 127.0.0.1:*/localhost:* — public Host headers then get 421.
_MCP_ALLOWED_HOSTS = [
    "127.0.0.1:*",
    "localhost:*",
    "[::1]:*",
    "legislation.scriptkitty.yachts",
    "legislation.scriptkitty.yachts:*",
    "rpc.scriptkitty.yachts",
    "rpc.scriptkitty.yachts:*",
    "mcp.scriptkitty.yachts",
    "mcp.scriptkitty.yachts:*",
    "dev.scriptkitty.yachts",
    "dev.scriptkitty.yachts:*",
]
_MCP_ALLOWED_ORIGINS = [
    "http://127.0.0.1:*",
    "http://localhost:*",
    "http://[::1]:*",
    "https://legislation.scriptkitty.yachts",
    "https://rpc.scriptkitty.yachts",
    "https://mcp.scriptkitty.yachts",
    "https://dev.scriptkitty.yachts",
]

# FastMCP sub-app — Mount strips /mcp prefix, so route must be at "/"
mcp = FastMCP(
    "legislation-explorer",
    streamable_http_path="/",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_MCP_ALLOWED_HOSTS,
        allowed_origins=_MCP_ALLOWED_ORIGINS,
    ),
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_CASE_CITATION_RE = _re.compile(r'\[(\d{4})\]\s*([A-Z]+(?:\s*[A-Z]+)*)\s*(\d+)')

def _normalise_case_citation(raw: str) -> str | None:
    m = _CASE_CITATION_RE.search(raw)
    if m:
        return f"[{m.group(1)}] {m.group(2)} {m.group(3)}"
    return None

# ---------------------------------------------------------------------------
# Auth middleware — applied to the streamable_http_app in main.py
# ---------------------------------------------------------------------------

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.requests import Request
import json

# OAuth token validation
from backend.oauth_provider import provider as oauth_provider


class MCPAuthMiddleware(BaseHTTPMiddleware):
    """Token auth + rate limiting for MCP endpoints.

    Accepts token from:
      - Authorization: Bearer ***
      - X-API-Key: *** (alternative to Bearer, for Cloudflare WAF bypass)
      - ?token=<token> query param
      - /mcp/<token>  path segment (bypasses Cloudflare WAF)
    Skips auth when DEV_MODE=true.
    """

    async def dispatch(self, request: Request, call_next):
        if os.environ.get("DEV_MODE", "").lower() in ("true", "1", "yes"):
            return await call_next(request)

        token = ""
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
        if not token:
            token = request.headers.get("X-API-Key", "")
        if not token:
            token = request.query_params.get("token", "")
        if not token:
            token = request.query_params.get("v", "")
        if not token:
            token = request.query_params.get("_auth", "")
        if not token:
            token = request.query_params.get("x", "")
        # Path-segment token: /mcp/<token>
        if not token:
            path = request.url.path
            if path.startswith("/api/cadena/mcp/") and len(path) > 16:
                token = path.split("/api/cadena/mcp/", 1)[-1].split("?")[0].split("/")[0]
            elif path.startswith("/api/private/mcp/") and len(path) > 18:
                token = path.split("/api/private/mcp/", 1)[-1].split("?")[0].split("/")[0]
            elif path.startswith("/mcp/") and len(path) > 5:
                token = path.split("/mcp/", 1)[-1].split("?")[0].split("/")[0]
            elif path.startswith("/api/rpc/") and len(path) > 10:
                token = path.split("/api/rpc/", 1)[-1].split("?")[0].split("/")[0]

        # Body-based auth (JSON-RPC params._auth) — bypasses Cloudflare WAF
        if not token:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body = json.loads(body_bytes)
                    params = body.get("params", {})
                    if isinstance(params, dict):
                        token = params.get("_auth", "") or params.get("token", "")
            except Exception:
                pass

        # Cookie-based auth — Cloudflare doesn't inspect cookies as credentials
        if not token:
            token = request.cookies.get("token", "")

        # Custom header auth — X-Session-Id bypasses Cloudflare DDoS
        if not token:
            token = request.headers.get("X-Session-Id", "")

        if not token:
            return Response("Missing token", status_code=401,
                            headers={"WWW-Authenticate": "Bearer"})

        if not token_manager.validate_token(token):
            # Fallback: try OAuth access token
            oauth_data = oauth_provider.load_access_token(token)
            if not oauth_data:
                return Response("Invalid or revoked token", status_code=403)

        allowed, reason = token_manager.check_rate_limit(token)
        if not allowed:
            return Response(reason, status_code=429)

        return await call_next(request)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def search_legislation(
    query: str,
    act: str | None = None,
    limit: int = 20,
) -> str:
    """Search legislation sections by keyword or section number.

    All query terms must appear in section text (AND matching).
    Section-number-shaped queries (e.g. '8-1') are exact-matched
    to rank the cited section first.
    """
    result = fts_search(query.strip(), act, limit=min(100, max(1, limit)))
    return json.dumps({
        "query": query,
        "total": result["total_count"],
        "results": result["results"],
    }, indent=2)


@mcp.tool()
async def get_section(act: str, section: str) -> str:
    """Retrieve full text of a legislation section.

    Leading s/sec/section is stripped automatically. Uses hyphenated format
    (8-1) for ITAA 1997/GST/TAA; unhyphenated (23AH) for ITAA 1936.
    """
    section = _re.sub(r'^(?:s(?:ec(?:tion)?)?\.?)\s+', '', section.strip(),
                      flags=_re.IGNORECASE).strip()

    if _re.match(r'^\d+(\.\d)', section):
        return json.dumps({
            "error": f"Section '{section}' not found. Use hyphenated format (e.g. 8-1) not dotted (8.1)."
        })

    has_hyphen = '-' in section
    is_1936 = act == 'itaa-1936'
    if has_hyphen and is_1936:
        return json.dumps({
            "error": f"Section {section} not found in itaa-1936; ITAA 1936 sections are unhyphenated (e.g. 23AH). Did you mean itaa-1997 s {section}?"
        })

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
        return json.dumps({"error": f"Section {section} not found"})

    md_path = DATA_DIR / act / "sections" / section_path
    if not md_path.exists():
        return json.dumps({"error": "Section file not found"})

    content = md_path.read_text(encoding="utf-8")
    body = content
    if content.startswith("---"):
        fm_end = _re.search(r'\n---\s*\n', content)
        if fm_end:
            body = content[fm_end.end():]

    body_clean = _re.sub(r'\n---\s*\*Last updated:.*?\*', '', body, flags=_re.DOTALL)
    body_clean = _re.sub(r'\n---\s*$', '', body_clean)
    body_stripped = body_clean.strip()
    truncated = bool(body_stripped) and not _re.search(r'[.\\)"\'!?]\s*$', body_stripped)

    return json.dumps({
        "act": act,
        "section": section,
        "body": body,
        "truncated": truncated,
    }, indent=2)


@mcp.tool()
async def list_acts() -> str:
    """List all available acts and ATO rulings."""
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
    return json.dumps({"acts": acts}, indent=2)


@mcp.tool()
async def get_act_tree(act: str, depth: str = "sections") -> str:
    """Get the full structure of an act (parts, divisions, sections).

    depth: 'parts' returns only parts (fast), 'divisions' includes divisions,
           'sections' (default) includes all sections.
    """
    tree = load_tree(act)
    if depth == "parts":
        pruned = {
            "act": tree.get("act", act),
            "compilation_no": tree.get("compilation_no"),
            "compilation_date": tree.get("compilation_date"),
            "depth": "parts",
            "parts": [{"id": p.get("id"), "title": p.get("title")}
                      for p in tree.get("parts", [])],
        }
        return json.dumps(pruned, indent=2)
    elif depth == "divisions":
        pruned = {
            "act": tree.get("act", act),
            "compilation_no": tree.get("compilation_no"),
            "compilation_date": tree.get("compilation_date"),
            "depth": "divisions",
            "parts": [],
        }
        for p in tree.get("parts", []):
            part = {"id": p.get("id"), "title": p.get("title"), "divisions": []}
            for d in p.get("divisions", []):
                part["divisions"].append({"id": d.get("id"), "title": d.get("title")})
            pruned["parts"].append(part)
        return json.dumps(pruned, indent=2)
    return json.dumps(tree, indent=2)


@mcp.tool()
async def get_definition(act: str, term: str) -> str:
    """Look up the definition of a term in an act.

    Returns the full definition text, not just a locator.
    """
    result = get_definition_text(act, term)
    if result:
        return json.dumps(result, indent=2)
    return json.dumps({"error": f"Definition for '{term}' not found in {act}"})


@mcp.tool()
async def get_rulings_for_section(act: str, section: str) -> str:
    """⚠️ DEPRECATED — Use get_case for case-related queries instead.
    This tool previously retrieved ATO rulings related to a legislation section.
    Rulings are better accessed via get_ruling(citation) directly."""
    return json.dumps({
        "deprecated": True,
        "message": "This tool is deprecated. Use get_ruling(citation) to look up "
                   "specific rulings directly, or get_info for coverage counts.",
        "replacement": "get_ruling",
        "action": f"Use get_ruling(citation=\"<TR 2024/1>\") to retrieve a specific ruling.",
    }, indent=2)


@mcp.tool()
async def search_cases(query: str, limit: int = 20) -> str:
    """Search case AI summaries and metadata by topic, case name, or citation.

    Searches across facts, issues, held, reasoning, outcome, cases_cited,
    and legislation_cited fields. Returns matching citations with summaries;
    use get_case for full details and download_case for full text URLs.
    """
    limit = min(100, max(1, limit))
    query = query.strip().lower()
    if not query:
        return json.dumps({"total": 0, "results": [], "note": "Query required"})

    summaries_dir = Path("/home/harrison/legislation-explorer/scripts/cleaned/summaries")
    results = []
    words = query.split()

    if summaries_dir.is_dir():
        for f in os.listdir(str(summaries_dir)):
            if not f.endswith(".json"):
                continue
            try:
                with open(summaries_dir / f) as fh:
                    s = json.load(fh)
            except Exception:
                continue
            text_parts = [
                s.get("citation", ""),
                s.get("case_name", ""),
                s.get("facts", ""),
                s.get("held", ""),
                s.get("reasoning", ""),
                s.get("outcome", ""),
            ]
            for lst_key in ("issues", "cases_cited", "legislation_cited"):
                val = s.get(lst_key, [])
                if isinstance(val, list):
                    text_parts.extend(str(item) for item in val
                                      if isinstance(item, str))
                elif isinstance(val, str):
                    text_parts.append(val)
            haystack = " ".join(text_parts).lower()
            if all(w in haystack for w in words):
                from urllib.parse import quote
                results.append({
                    "citation": s.get("citation", ""),
                    "case_name": s.get("case_name", ""),
                    "court": s.get("court", ""),
                    "year": s.get("citation", "")[1:5]
                    if s.get("citation", "").startswith("[") else "",
                    "has_summary": True,
                    "html_url": f"https://legislation.scriptkitty.yachts/tax-cases/{quote(s.get('citation', ''))}",
                })

    # Also search PostgreSQL for cases with metadata but no summary
    if len(results) < limit * 2:
        safe = query.replace("'", "''")
        try:
            import subprocess
            like_clause = " OR ".join(
                f"c.case_name ILIKE '%{w}%' OR c.citation ILIKE '%{w}%'"
                for w in words
            )
            r = subprocess.run(
                ["docker", "exec", "cadena-postgres", "psql", "-U", "postgres",
                 "-d", "cadena_knowledge", "-tA",
                 "-c", f"SELECT c.citation, c.case_name, c.court FROM cases c "
                       f"WHERE ({like_clause}) ORDER BY c.citation LIMIT {limit};"],
                capture_output=True, text=True, timeout=10
            )
            for line in r.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("|", 2)
                cit = parts[0].strip()
                name = parts[1].strip() if len(parts) > 1 else ""
                court = parts[2].strip() if len(parts) > 2 else ""
                if any(r["citation"] == cit for r in results):
                    continue
                from urllib.parse import quote
                results.append({
                    "citation": cit,
                    "case_name": name,
                    "court": court,
                    "year": cit[1:5] if cit.startswith("[") else "",
                    "has_summary": False,
                    "html_url": f"https://legislation.scriptkitty.yachts/tax-cases/{quote(cit)}",
                })
        except Exception:
            pass

    return json.dumps({
        "total": len(results),
        "results": results[:limit],
        "note": "Searches AI summaries and case metadata. Results with summaries are "
                "richer than metadata-only results. Use get_case for full details.",
    }, indent=2)


@mcp.tool()
async def get_info() -> str:
    """Return server version, usage conventions, tool descriptions, and coverage counts.

    Call this first to understand how to use each MCP tool.
    """
    rulings_count = len(load_rulings())
    try:
        import subprocess
        r = subprocess.run(
            ["docker", "exec", "cadena-postgres", "psql", "-U", "postgres",
             "-d", "cadena_knowledge", "-tA",
             "-c", "SELECT COUNT(*) FROM cases c WHERE EXISTS "
                   "(SELECT 1 FROM case_paragraphs cp WHERE cp.case_id = c.id);"],
            capture_output=True, text=True, timeout=10
        )
        cases_count = int(r.stdout.strip())
    except Exception:
        cases_count = 7375

    summaries_dir = "/home/harrison/legislation-explorer/scripts/cleaned/summaries"
    summaries_count = len([f for f in os.listdir(summaries_dir)
                          if f.endswith(".json")]) if os.path.isdir(summaries_dir) else 0

    return json.dumps({
        "name": "Legislation Explorer",
        "version": VERSION,
        "usage": {
            "act_ids": {
                "itaa-1997": "Income Tax Assessment Act 1997",
                "itaa-1936": "Income Tax Assessment Act 1936",
                "gst-1999": "GST Act 1999",
                "taa-1953": "TAA 1953",
                "nz-it-2007": "NZ Income Tax Act 2007",
                "master-tax-guide": "Australian Master Tax Guide (commentary)",
                "master-gst-guide": "Australian Master GST Guide (commentary)",
                "master-tax-examples": "Australian Master Tax Examples (commentary)",
                "rulings": "ATO rulings corpus",
            },
            "section_format": {
                "itaa-1997": "Hyphenated: 8-1, 6-5, 995-1",
                "itaa-1936": "Unhyphenated: 23AH, 109Z, 177D",
                "gst-1999": "Hyphenated: 195-1",
                "taa-1953": "Schedule 1: 284-15",
            },
            "citation_format": {
                "rulings": {"accepted": ["TR 2024/1", "PCG 2017/13"], "types": ["TR", "TD", "PCG", "PS LA", "LCG", "AID", "IT"]},
                "cases": {"required": "Bracketed medium-neutral form: [2024] HCA 1", "courts": ["HCA", "FCAFC", "FCA", "ARTA"]},
            },
            "workflows": {
                "find a provision": "search_legislation(query, act?) -> get_section(act, section)",
                "browse an act": "get_act_tree(act, depth='parts') -> get_section",
                "defined term": "get_definition(act, term)",
                "ATO guidance": "get_ruling(citation) — look up a specific ruling",
                "case by name or topic": "search_cases(query) -> get_case(citation) — includes summary, refs, citations, links",
                "case references": "case_legislation_refs(citation) — legislation refs + case citations",
                "download judgment": "case_link(citation) — court → AustLII → hosted HTML URLs",
            },
            "coverage": {
                "acts": "compilation 2026-04-01 (most acts)",
                "rulings": rulings_count,
                "cases_in_db": cases_count,
                "cases_with_summaries": summaries_count,
            },
        },
    }, indent=2)


@mcp.tool()
async def get_ruling(citation: str) -> str:
    """Retrieve an ATO ruling preview by citation.

    Returns metadata and a content preview (~5K chars). Full text is
    available via the ATO or AustLII URLs in the response.
    Accepts TR 2020/1, TR_2020_1, or TR 2024/1 formats.
    """
    CITATION_ALIASES = {"LCR": "LCG"}
    normalized = _re.sub(r'[\s/]+', '_', citation).strip('_')
    candidates = {normalized}
    prefix_m = _re.match(r'^([A-Za-z]+)_(.*)$', normalized)
    if prefix_m and prefix_m.group(1).upper() in CITATION_ALIASES:
        candidates.add(f"{CITATION_ALIASES[prefix_m.group(1).upper()]}_{prefix_m.group(2)}")

    for r in load_rulings():
        if r["citation"] in candidates:
            path = Path(r["source"])
            content = path.read_text(encoding="utf-8") if path.exists() else ""
            from backend.services.data_loader import _strip_ato_chrome
            stripped = _strip_ato_chrome(content)
            MAX_PREVIEW = 5000
            preview = stripped[:MAX_PREVIEW]
            truncated = len(stripped) > MAX_PREVIEW
            return json.dumps({
                "citation": r["citation"],
                "citation_display": r.get("citation_display", ""),
                "title": r["title"],
                "full_title": r.get("full_title", ""),
                "type": r["type"],
                "year": r["year"],
                "withdrawn": r.get("withdrawn", False),
                "ato_url": r.get("ato_url", ""),
                "austlii_url": r.get("austlii_url", ""),
                "content_preview": preview,
                "content_truncated": truncated,
                "total_content_length": len(stripped),
            }, indent=2)

    return json.dumps({"error": f"Ruling {citation} not found"})


@mcp.tool()
async def get_case(
    citation: str,
) -> str:
    """Get case metadata, AI summary, legislation references, case citations, and download links.

    Returns structured summary with facts, issues, held, reasoning, outcome,
    cases cited, legislation cited, and download URLs for full judgment text.
    """
    from urllib.parse import quote
    citation_norm = _normalise_case_citation(citation) or citation
    dev_site_url = f"https://dev.scriptkitty.yachts/tax-cases/{quote(citation_norm)}"
    download_urls = build_download_urls(citation_norm)

    safe_name = citation_norm.replace(" ", "_").replace("[", "").replace("]", "").replace("/", "_")
    summary_path = Path("/home/harrison/legislation-explorer/scripts/cleaned/summaries") / f"{safe_name}.json"
    summary = None
    if summary_path.exists():
        try:
            with open(summary_path) as f:
                summary = json.load(f)
        except Exception:
            pass

    # Fetch case metadata (always includes legislation refs)
    result = get_case_metadata(citation_norm, include_legislation_refs=True)
    if result is None:
        return json.dumps({
            "error": f"Case not found in database: {citation_norm}",
            "hint": "Try search_cases to verify the citation format, "
                    "or check format — required: [2024] HCA 1",
        })

    # Fetch case citations (cited cases + cited-by)
    refs = get_case_references(citation_norm)

    result["summary"] = summary
    result["legislation_refs"] = result.pop("legislation_refs", [])
    result["case_citations"] = refs.get("case_citations", [])
    result["cited_by"] = refs.get("cited_by", [])
    result["download_urls"] = {
        "html_url": dev_site_url,
        "austlii_url": download_urls.get("austlii_url") if download_urls else None,
        "court_url": download_urls.get("court_url") if download_urls else None,
    }
    return json.dumps(result, indent=2)


@mcp.tool()
async def case_legislation_refs(citation: str) -> str:
    """Get legislation references and case citations for a case.

    Returns all legislation sections cited in the case, cases cited by the
    case, and cases that cite this case. Use case_link for download URLs
    and get_case for the full combined view.
    """
    from urllib.parse import quote
    citation_norm = _normalise_case_citation(citation) or citation
    refs = get_case_references(citation_norm)

    return json.dumps({
        "citation": citation_norm,
        "legislation_refs": refs.get("legislation_refs", []),
        "case_citations": refs.get("case_citations", []),
        "cited_by": refs.get("cited_by", []),
    }, indent=2)


@mcp.tool()
async def case_link(citation: str) -> str:
    """Get download links for a case: court website, AustLII, and hosted HTML.

    Ordered by preference: court URL first (most authoritative),
    then AustLII, then hosted HTML.
    """
    from urllib.parse import quote
    citation_norm = _normalise_case_citation(citation) or citation
    result = build_download_urls(citation_norm)
    if result is None:
        return json.dumps({"error": f"Could not parse or find case: {citation}"})

    dev_url = f"https://legislation.scriptkitty.yachts/tax-cases/{quote(citation_norm)}"
    ordered = {
        "citation": result.get("citation"),
        "case_name": result.get("case_name"),
        "court_url": result.get("court_url"),
        "austlii_url": result.get("austlii_url"),
        "html_url": result.get("html_url", dev_url),
        "content_length": result.get("content_length"),
        "paragraph_count": result.get("paragraph_count"),
        "note": ("Full text available for download. Court website is most authoritative, "
                 "then AustLII, then hosted HTML."),
    }
    return json.dumps(ordered, indent=2)


@mcp.tool()
async def list_rulings(
    type: str | None = None,
    year: int | None = None,
    limit: int = 100,
    offset: int = 0,
    counts_only: bool = False,
) -> str:
    """List all ATO rulings grouped by year and type.

    Returns the full ruling tree with ATO.gov.au and AustLII links.
    """
    rulings = load_rulings()

    if type:
        filter_type = type.upper()
        rulings = [r for r in rulings if r.get("type", "").upper() == filter_type]
    if year:
        rulings = [r for r in rulings if r.get("year") == year]

    if counts_only:
        years: dict = {}
        no_year: dict = {}
        for r in rulings:
            y = r.get("year", 0)
            t = r.get("type", "Ruling")
            if y == 0:
                no_year[t] = no_year.get(t, 0) + 1
            else:
                if y not in years:
                    years[y] = {}
                years[y][t] = years[y].get(t, 0) + 1
        payload = {
            "mode": "counts_only",
            "total_rulings": len(rulings),
            "by_year": years,
        }
        if no_year:
            payload["no_year"] = no_year
            payload["no_year_total"] = sum(no_year.values())
            payload["note"] = (
                f"Rulings without a year field ({sum(no_year.values())} total) "
                f"grouped under 'no_year'."
            )
        return json.dumps(payload, indent=2)

    if limit > 0:
        rulings = rulings[offset:offset + limit]
    elif offset > 0:
        rulings = rulings[offset:]

    years_dict: dict = {}
    no_year_items = []
    for r in rulings:
        y = r.get("year", 0)
        t = r.get("type", "Ruling")
        if y == 0:
            no_year_items.append(r)
            continue
        if y not in years_dict:
            years_dict[y] = {}
        if t not in years_dict[y]:
            years_dict[y][t] = []
        years_dict[y][t].append({
            "citation": r["citation"],
            "citation_display": r.get("citation_display", ""),
            "title": r.get("full_title", r.get("title", "")),
            "withdrawn": r.get("withdrawn", False),
            "ato_url": r.get("ato_url", ""),
            "austlii_url": r.get("austlii_url", ""),
        })

    payload = {
        "ato_rulings_total": len(rulings),
        "filter_type": type,
        "filter_year": year,
        "by_year": years_dict,
    }
    if no_year_items:
        payload["no_year"] = [
            {"citation": r["citation"], "title": r.get("full_title", r.get("title", "")),
             "withdrawn": r.get("withdrawn", False), "ato_url": r.get("ato_url", ""),
             "austlii_url": r.get("austlii_url", "")}
            for r in no_year_items
        ]
        payload["no_year_total"] = len(no_year_items)
        payload["note"] = (
            f"Rulings without a year field ({len(no_year_items)} total) listed under 'no_year'."
        )

    return json.dumps(payload, indent=2)


@mcp.tool()
async def get_case_paragraphs(citation: str) -> str:
    """⚠️ DEPRECATED — Full paragraph text is no longer stored.
    Use get_case to retrieve the summary + download links."""
    return json.dumps({
        "deprecated": True,
        "message": "Full paragraph text is no longer stored.",
        "replacement": "get_case",
        "action": f"Use get_case(citation=\"{citation}\") to retrieve the AI summary "
                  f"and download links.",
    }, indent=2)


@mcp.tool()
async def search_case_paragraphs(query: str) -> str:
    """⚠️ DEPRECATED — Full paragraph text is no longer indexed.
    Use search_cases to find cases by summary content."""
    return json.dumps({
        "deprecated": True,
        "message": "Full paragraph text is no longer stored.",
        "replacement": "search_cases",
        "action": f"Use search_cases(query=\"{query}\") to search case AI summaries.",
    }, indent=2)


@mcp.tool()
async def download_case(citation: str) -> str:
    """⚠️ DEPRECATED — Use case_link instead.
    Get download links for a case: court website, AustLII, and hosted HTML."""
    import warnings
    warnings.warn("download_case is deprecated, use case_link", DeprecationWarning)
    return await case_link(citation)
