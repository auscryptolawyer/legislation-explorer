"""
backend/main.py — FastAPI app for Legislation Explorer.

Serves:
  - React SPA static files
  - JSON API for tree, sections, definitions, search
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Legislation Explorer")

# CORS — allow same-origin and Tailnet
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = Path.home() / "legislation-explorer"
DATA_DIR = BASE / "data"
FRONTEND_DIST = BASE / "frontend" / "dist"

BEARER_TOKEN = os.environ.get("LEGISLATION_BEARER_TOKEN", "")

# ---------------------------------------------------------------------------
# Auth middleware (disabled — personal tool, Cloudflare-proxied)
# ---------------------------------------------------------------------------

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    return await call_next(request)


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

_acts_cache: dict[str, dict] = {}
_definitions_cache: dict[str, dict[str, dict]] = {}


def load_tree(act: str) -> dict:
    if act not in _acts_cache:
        path = DATA_DIR / act / "tree.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Act {act} not found")
        _acts_cache[act] = json.loads(path.read_text(encoding="utf-8"))
    return _acts_cache[act]


_definition_regex_cache: dict[str, re.Pattern] = {}


def load_definitions(act: str) -> dict[str, dict]:
    if act not in _definitions_cache:
        path = DATA_DIR / "definitions.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            act_data = data.get(act, {})
            terms = act_data.get("terms", {})
            defs = {}
            for term, info in terms.items():
                defs[term.lower()] = {**info, "section": act_data.get("section", "")}
            _definitions_cache[act] = defs
        else:
            _definitions_cache[act] = {}
    return _definitions_cache[act]


def get_definition_regex(act: str) -> re.Pattern | None:
    if act not in _definition_regex_cache:
        defs = load_definitions(act)
        if not defs:
            return None
        terms = sorted(defs.items(), key=lambda x: len(x[0]), reverse=True)
        patterns = [rf'(?<![\w-]){re.escape(term)}(?![\w-])' for term, _ in terms]
        _definition_regex_cache[act] = re.compile('|'.join(patterns), re.IGNORECASE)
    return _definition_regex_cache[act]


def link_definitions(markdown: str, act: str) -> str:
    defs = load_definitions(act)
    regex = get_definition_regex(act)
    if not regex:
        return markdown

    def replacer(m: re.Match) -> str:
        matched = m.group(0)
        key = matched.lower()
        info = defs.get(key)
        if info:
            return f'[{matched}](/{act}/s{info["section"]}#{info["anchor"]})'
        return matched

    tokens = []
    split_re = re.compile(r'(```[\s\S]*?```|`[^`]+`|\[[^\]]+\]\([^)]+\))')
    last = 0
    for m in split_re.finditer(markdown):
        if m.start() > last:
            tokens.append(('text', regex.sub(replacer, markdown[last:m.start()])))
        tokens.append(('code', m.group(0)))
        last = m.end()
    if last < len(markdown):
        tokens.append(('text', regex.sub(replacer, markdown[last:])))

    return ''.join(t[1] for t in tokens)


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/acts")
def list_acts():
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
    return acts


@app.get("/api/tree/{act}")
def get_tree(act: str):
    return load_tree(act)


@app.get("/api/section/{act}/{section}")
def get_section(act: str, section: str):
    tree = load_tree(act)
    # Find section path from tree
    section_path = None
    for part in tree.get("parts", []):
        # Sections directly under part (ITAA 1936 style)
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
        # Fallback: direct filesystem lookup
        for md in (DATA_DIR / act / "sections").rglob(f"{section}.md"):
            section_path = str(md.relative_to(DATA_DIR / act / "sections"))
            break

    if not section_path:
        raise HTTPException(status_code=404, detail=f"Section {section} not found")

    md_path = DATA_DIR / act / "sections" / section_path
    if not md_path.exists():
        raise HTTPException(status_code=404, detail=f"Section file not found")

    content = md_path.read_text(encoding="utf-8")
    # Parse frontmatter
    fm = {}
    if content.startswith("---"):
        fm_end = content.find("---", 3)
        fm_text = content[3:fm_end].strip()
        for line in fm_text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip().strip('"')
        body = content[fm_end + 3:]
    else:
        body = content

    body = link_definitions(body, act)

    return {"frontmatter": fm, "markdown": body}


@app.get("/api/definitions/{act}")
def get_definitions(act: str):
    defs = load_definitions(act)
    return {"act": act, "count": len(defs), "terms": defs}


@app.get("/api/definition/{act}/{term}")
def get_definition(act: str, term: str):
    defs = load_definitions(act)
    key = term.lower()
    if key in defs:
        return defs[key]
    # Try slugified key
    slug = re.sub(r"[^a-z0-9\s-]", "", key).strip()
    slug = re.sub(r"\s+", "-", slug)
    for k, v in defs.items():
        if v.get("anchor") == f"s995-1-{slug}" or v.get("anchor") == f"s6-{slug}":
            return v
    raise HTTPException(status_code=404, detail=f"Definition for '{term}' not found")


@app.get("/api/search")
def search(q: str, act: str | None = None):
    results = []
    acts_to_search = [act] if act else [d.name for d in DATA_DIR.iterdir() if d.is_dir()]

    for a in acts_to_search:
        try:
            tree = load_tree(a)
        except HTTPException:
            continue
        q_lower = q.lower()
        for part in tree.get("parts", []):
            # Part-level sections (ITAA 1936)
            for sec in part.get("sections", []):
                if q_lower in sec["id"].lower() or q_lower in sec.get("title", "").lower():
                    results.append({
                        "act": a,
                        "section": sec["id"],
                        "title": sec.get("title", ""),
                        "path": sec["path"],
                    })
            for div in part.get("divisions", []):
                for sec in div.get("sections", []):
                    if q_lower in sec["id"].lower() or q_lower in sec.get("title", "").lower():
                        results.append({
                            "act": a,
                            "section": sec["id"],
                            "title": sec.get("title", ""),
                            "path": sec["path"],
                        })
                for sub in div.get("subdivisions", []):
                    for sec in sub.get("sections", []):
                        if q_lower in sec["id"].lower() or q_lower in sec.get("title", "").lower():
                            results.append({
                                "act": a,
                                "section": sec["id"],
                                "title": sec.get("title", ""),
                                "path": sec["path"],
                            })

    return {"results": results[:50]}


# ---------------------------------------------------------------------------
# Static files / SPA fallback
# ---------------------------------------------------------------------------

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index, headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})
        return HTMLResponse("<h1>Legislation Explorer</h1><p>Frontend not built yet.</p>")
