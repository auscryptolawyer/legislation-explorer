# Legislation Explorer — Project Scope

**Path:** ~/legislation-explorer/
**Master scope:** ~/PROJECT_SCOPE.md
**Changelog:** ~/CHANGELOG.md

## URLs
- **Production:** legislation.scriptkitty.yachts (tunnel → localhost:8765)
- **Dev:** dev.scriptkitty.yachts (tunnel → Vite :3000 → proxy /api → :8765)
- **Local backend:** http://127.0.0.1:8765/docs

## Architecture
- **Backend:** FastAPI + uvicorn (systemd: legislation-explorer.service) on :8765
- **Frontend:** React + Vite. Prod build at frontend/dist/ served by backend. Dev at :3000 (systemd: legislation-dev-frontend.service)
- **DB:** SQLite files (search_index.db, comments.db, mcp_tokens.db) at project root

## Key Backend Files
- backend/main.py — app entry, static file mount
- backend/config.py — RULING_DIR, ATO_RULING_DIR, COMMENTARY_DIR, CASE_DIR
- backend/services/data_loader.py — load_rulings(), get_act_section_content()
- backend/routes/rulings.py — /api/rulings-list, /api/ruling/{citation}
- backend/routes/acts.py — legislation tree
- backend/routes/search.py — search
- backend/routes/tax_cases.py — tax cases
- backend/routes/definitions.py — definitions
- backend/routes/commentary.py — commentary

## Data Sources
- **Rulings (including ATO IDs):** ~/projects/cadena-knowledge-MCP/data/rulings/ (6,618 .txt files)
- **ATO rulings (subdirs):** ~/projects/cadena-knowledge-MCP/data/ato_rulings/{td,tr,pcg,ps_la}/
- **Cases:** ~/projects/asic-scraper/cases/
- **Commentary:** ~/projects/cadena-knowledge-MCP/pipeline/output/
- **Tax cases JSON:** ~/legislation-explorer/data/{hca,fca,fcafc,aata}_tax_cases.json

## ATO ID Pipeline
- Existence: pipeline/scrape_ato_ids.py (curl_cffi + title check)
- Content: pipeline/fetch_ato_id_content.py (print view)
- Files: AID_{year}_{num}.txt (5,931 files, full content)
- Print view URL: /law/view/print?DocID=AID/AID{year}{num}/00001

## Authentication
- Azure AD (tenant/client IDs in config)
- Bearer token in .env
- Cadena content gated at /api/cadena/*

## Startup
- ~10s for BGE embedding model download/load
- Deployed via systemd user service, restart on failure
