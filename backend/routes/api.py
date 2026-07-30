"""API route assembly."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from .acts import router as acts_router
from .definitions import router as definitions_router
from .search import router as search_router
from .cases import router as cases_router
from .rulings import router as rulings_router
from .commentary import router as commentary_router
from .comments import router as comments_router
from .tax_cases import router as tax_cases_router
from .user_prefs import router as user_prefs_router
from .admin import router as admin_router
from .data_versions import router as data_versions_router

router = APIRouter()
router.include_router(acts_router)
router.include_router(definitions_router)
router.include_router(search_router)
router.include_router(cases_router)
router.include_router(rulings_router)
router.include_router(commentary_router)
router.include_router(comments_router)
router.include_router(tax_cases_router)
router.include_router(user_prefs_router)
router.include_router(admin_router)
router.include_router(data_versions_router)


VERSION = "2.6.0"

CHANGELOG = [
    {
        "version": "2.5.0",
        "date": "2026-07-29",
        "title": "Rulings sidebar + dedicated pages, court-grouped cases, hyperlinked cross-references",
        "changes": [
            "Rulings sidebar tree (act='rulings') — browse by year → type, click to open full text",
            "Dedicated /rulings/{citation} pages for all 7,310 ATO rulings — full text + referenced sections",
            "Fixed URL routing for ruling citations with slashes (TR 2025/1, PS LA 2011/10)",
            "Cases on section pages now grouped by court: High Court, Full Federal Court, Federal Court, AAT",
            "Legislation references in case detail pages are hyperlinked — click to navigate to the section",
            "Case citations on section pages are hyperlinked — click to open the tax case page",
            "Version bumped to 2.5.0",
        ],
    },
    {
        "version": "2.4.0",
        "date": "2026-07-27",
        "title": "Search includes rulings, pagination, full-page results, related content panel, tree view",
        "changes": [
            "Flat search now includes 6,618 ATO rulings alongside legislation sections — FTS5 rulings_fts virtual table indexed from ruling text files",
            "Search results paginated at 25 per page with page number buttons and Previous/Next navigation",
            "Full-page search results layout — results flow naturally below search bar, homepage expands to full width, welcome footer hidden while searching",
            "Source filter now re-applies to existing results — selecting/deselecting acts in the filter immediately narrows results",
            "Display fixes: no more 's' prefix on CCH guide sections, left-aligned snippets with FTS5 highlights, long titles wrap instead of truncating",
            "Drawer icon (three-line SVG) at top-left of main pane on mobile — opens sidebar, separate from search bar",
            "Definitions are clickable — tapping a defined term navigates to the defining section with anchor",
            "Commentary, Cases, and Rulings sections consolidated into unified 'Related' panel with subsections: Sections, Rulings, Defined Terms, Cases (placeholder), Commentary (placeholder)",
            "Rulings in Related panel display proper display names (TR 2023/2) not raw citations (TR_2023_2)",
            "Tree view in main content pane when browsing an act — all parts expanded, select a section to open content",
            "Auto-build search index on flat search request when index is missing",
        ],
    },
    {
        "version": "2.3.1",
        "date": "2026-07-25",
        "title": "ATO rulings URLs fixed, IT rulings indexed, MCP tools enhanced",
        "changes": [
            "ATO ruling URLs switched from dead /law/view/pdf/ and URL-encoded DocID to working plain-slash DocID + &PiT=99991231235958 format",
            "233 IT rulings (IT 1→363) extracted from Postgres and added to the rulings tree",
            "PS LA citation parsing fixed — citations like PS_LA_2011_10 now display and link correctly",
            "New MCP tool: list_rulings — returns all 388 rulings grouped by year/type with ATO.gov.au and AustLII links",
            "MCP get_ruling now includes ato_url, austlii_url, and citation_display fields",
            "MCP get_rulings_for_section passes through enriched data including ATO URLs",
        ],
    },
    {
        "version": "2.3.0",
        "date": "2026-07-25",
        "title": "Microsoft SSO, public content, Cadena IP gating",
        "changes": [
            "Microsoft Entra ID SSO — sign in with @cadenalegal.com.au account",
            "All existing content (legislation, rulings, cases, search) is now public — no login required",
            "Cadena IP content (precedents, strategies, research) gated behind login",
            "Auth middleware restructured: only /api/cadena/* and /mcp/cadena/* require authentication",
        ],
    },
    {
        "version": "2.2.0",
        "date": "2026-07-25",
        "title": "Case MCP tools, enriched case detail, shareable URLs, head_notes fix",
        "changes": [
            "New MCP tool: get_case — case metadata with section-type outline (no paragraph text)",
            "New MCP tool: get_case_paragraphs — paragraph content filtered by section type, paginated, capped at 100/50K chars",
            "New MCP tool: search_case_paragraphs — FTS across 7,377 cases, optional citation scope",
            "New MCP tool: download_case — AustLII download URLs for offline research",
            "Case detail view in UI enriched with judges, outcome, paragraph count, file size, linked legislation",
            "Share button in sidebar — copies current page URL to clipboard (supports sections, rulings, tax cases)",
            "Direct URL loading for tax cases — e.g. /tax-cases/%5B2026%5D%20FCAFC%2010 navigates straight to the case",
            "Bug fix: head_notes incorrectly parsed as flat array instead of JSON object — _infer_type now checks JSON before PG array literal",
            "Bug fix: case endpoint now falls back to Postgres DB for cases not in flat JSON files",
            "Bug fix: DB-only cases now extract catchwords from head_notes JSON",
        ],
    },
    {
        "version": "2.1.2",
        "date": "2026-07-25",
        "title": "ATO rulings: year fix, LCR→LCG alias, full titles, PDF extraction, MCP enrichment; get_definition fixes & GST metadata",
        "changes": [
            "Bug fix: get_rulings_for_section no longer returns year=0 — year extracted from filename regex fallback in citation_index builder",
            "Bug fix: get_ruling now normalises LCR → LCG citation alias (ATO publishes as LCR, files stored as LCG)",
            "Bug fix: get_definition no longer requires definitions at column 0 — uses (?<!\\w) lookbehind to match inline text, so ITAA 1936 'dividend' (s 6(1)) and GST 'enterprise' (s 195-1) now resolve correctly",
            "Bug fix: GST compilation metadata updated — all 824 section files from compilation 96 (2026-01-01) to compilation 228 (2026-04-01) to match tree.json",
            "load_rulings now extracts descriptive full_title from ruling text content (e.g. 'Income tax: whether penalty interest is deductible')",
            "21 ATO ruling PDFs (1 TD + 20 TR) extracted to text and indexed in citation_index via pipeline/extract_ato_ruling_pdfs.py",
            "MCP get_rulings_for_section enriched with load_rulings() data (proper year, full_title)",
            "MCP get_ruling returns full_title field, supports LCR→LCG alias",
            "Rulings list in sidebar shows citation + full descriptive title",
            "Section view ruling links display proper citation (TR 2019/2) not internal filename (TR_2019_2)",
        ],
    },
    {
        "version": "2.1.1",
        "date": "2026-07-24",
        "title": "get_definition now returns definition text, not just a pointer",
        "changes": [
            "get_definition now resolves the anchor server-side and returns the full definition text (body, anchor, section)",
            "Removed load_definitions import — get_definition_text does complete lookup internally",
        ],
    },
    {
        "version": "2.1.0",
        "date": "2026-07-24",
        "title": "Simplified MCP tools, year fix, citation normalization & get_info tool",
        "changes": [
            "MCP tools simplified: removed get_case and get_cases_for_section — all case lookup via search_cases",
            "get_ruling now accepts TR 2020/1, TR_2020_1, or TR 2024/1 (mixed spacing/slash formats)",
            "Ruling year field fixed — was always 0, now correctly parsed from citation for all ruling types",
            "New get_info MCP tool — returns version, changelog, and tool list (no args)",
            "get_rulings_for_section tool description updated",
        ],
    },
    {
        "version": "2.0.0",
        "date": "2026-07-24",
        "title": "Tax Cases, CCH Titles, Hall of Fame & Code-splitting",
        "changes": [
            "6,701 tax cases across HCA, FCA, FCAFC, and AAT (ARTA) — searchable and browsable",
            "Cases appear as collapsible tree in sidebar: Court → Year → Case",
            "Unified search bar in main pane — searches all acts, CCH guides, rulings, and cases simultaneously",
            "CCH Master Tax Guide and Master Tax Examples — backfilled 45 chapter titles and section titles",
            "TAA Schedule 1 renamed from 'Part UNKNOWN' — all 74 divisions now visible and expandable",
            "MCP Hall of Fame — named tokens, call logging, daily/weekly/monthly/all-time leaderboard",
            "Scrolling Hall of Fame banner at top of page with dismiss + modal popup",
            "Frontend code-split: bundle reduced from 507 KB to 170 KB (11 lazy-loaded chunks)",
            "MCP token creation requires name input",
            "MCP case tools simplified: removed get_case and get_cases_for_section — all case lookup via search_cases (name + catchwords → weblink)",
            "Monthly automated sync: scrapes AustLII, ingests into SQL + JSON, restarts server",
            "Concurrent scraping (5x parallel) for faster monthly updates",
            "2026 cases: 163 tax cases across all courts",
        ],
    },
    {
        "version": "1.0.0",
        "date": "2026-05-17",
        "title": "Initial Release",
        "changes": [
            "Legislation browser with ITAA 1997, ITAA 1936, GST Act, TAA 1953, and more",
            "Full-text search across acts and rulings",
            "ATO rulings database (TR, TD, PCG, PS LA)",
            "MCP integration for Claude Desktop",
            "Pinned tabs, comments, keyboard shortcuts",
        ],
    },
]


@router.get("/api/info")
def api_info():
    """Return version, changelog, and available endpoints."""
    return {
        "name": "Legislation Explorer",
        "version": VERSION,
        "changelog": CHANGELOG,
        "docs_url": "/docs",
        "endpoints": {
            "legislation": {
                "GET /api/acts": "List all available acts and rulings",
                "GET /api/tree/{act}": "Get the full structure of an act",
                "GET /api/section/{act}/{section}": "Retrieve full text of a section",
                "GET /api/search": "Search sections by keyword or number",
                "GET /api/definitions/{act}": "Look up definitions in an act",
            },
            "rulings": {
                "GET /api/rulings": "List all ATO rulings",
                "GET /api/ruling/{citation}": "Retrieve a ruling by citation",
                "GET /api/rulings-for-section/{act}/{section}": "Get rulings related to a section",
            },
            "tax_cases": {
                "GET /api/tax-cases/search": "Search tax cases by name, citation, or catchwords",
                "GET /api/tax-cases": "List available tax case sources (deprecated)",
                "GET /api/tax-cases/{court}": "Get cases for a court grouped by year (deprecated)",
                "GET /api/section-tax-cases/{act}/{section}": "Cases referencing a section (deprecated)",
            },
            "mcp": {
                "GET /mcp/sse": "SSE endpoint for MCP (requires token)",
                "POST /api/mcp-token": "Create an MCP access token",
                "GET /api/mcp-tokens": "List active MCP tokens",
                "POST /api/mcp-tokens/{token}/revoke": "Revoke an MCP token",
            },
            "system": {
                "GET /api/info": "This endpoint — version and documentation",
                "GET /health": "Health check",
                "GET /docs": "OpenAPI documentation (Swagger UI)",
            },
        },
    }
