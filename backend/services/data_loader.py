from __future__ import annotations

import functools
import json
import re
import logging
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from backend.config import DATA_DIR, COMMENTARY_DIR, CASE_DIR, RULING_DIR, ATO_RULING_DIR, PUBLICATION_NAMES, PUB_ACT_MAP

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Acts / sections
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def load_tree(act: str) -> dict:
    path = DATA_DIR / act / "tree.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Act {act} not found")
    return json.loads(path.read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=None)
def load_definitions(act: str) -> dict[str, dict]:
    path = DATA_DIR / "definitions_all.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    act_data = data.get(act, {})
    terms = act_data.get("terms", {})
    return {term.lower(): {**info} for term, info in terms.items()}


# ---------------------------------------------------------------------------
# Commentary
# ---------------------------------------------------------------------------

def _normalize_section_ref(ref: str, pub_name: str) -> tuple[str, str] | None:
    ref = ref.strip().replace("\n", " ")
    m = re.search(r's\s+(\d+[A-Z]?-[\d\(\) ]+(?:\(\d+\))?)', ref, re.IGNORECASE)
    if not m:
        return None
    section = m.group(1)
    lower = ref.lower()
    if "itaa97" in lower or "itaa 97" in lower:
        return ("itaa-1997", section)
    if "itaa36" in lower or "itaa 36" in lower:
        return ("itaa-1936", section)
    if "gst act" in lower or "gst 1999" in lower:
        return ("gst-1999", section)
    if "gst" in pub_name.lower():
        return ("gst-1999", section)
    return ("itaa-1997", section)


@functools.lru_cache(maxsize=None)
def _load_commentary_index() -> dict[str, list[dict]]:
    commentary_index: dict[str, list[dict]] = {}
    for filename, pub_display in PUBLICATION_NAMES.items():
        path = COMMENTARY_DIR / filename
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        pub_name = data.get("name", pub_display)
        for ch in data.get("chapters", []):
            for mh in ch.get("major_headings", []):
                all_refs: set[tuple[str, str]] = set()
                for cb in mh.get("content_blocks", []):
                    for ref in cb.get("section_refs", []):
                        norm = _normalize_section_ref(ref, pub_name)
                        if norm:
                            all_refs.add(norm)
                for sh in mh.get("sub_headings", []):
                    for cb in sh.get("content_blocks", []):
                        for ref in cb.get("section_refs", []):
                            norm = _normalize_section_ref(ref, pub_name)
                            if norm:
                                all_refs.add(norm)
                if all_refs:
                    entry = {
                        "publication": pub_name,
                        "chapter_number": ch.get("number"),
                        "chapter_title": ch.get("title"),
                        "heading_title": mh.get("title"),
                        "paragraph_number": mh.get("paragraph_number"),
                        "content_blocks": mh.get("content_blocks", []),
                        "sub_headings": mh.get("sub_headings", []),
                    }
                    for act, section in all_refs:
                        key = f"{act}:{section}"
                        if key not in commentary_index:
                            commentary_index[key] = []
                        commentary_index[key].append(entry)
    return commentary_index


def get_commentary_for_section(act: str, section: str, limit: int = 50, offset: int = 0) -> list[dict]:
    index = _load_commentary_index()
    key = f"{act}:{section}"
    entries = index.get(key, [])
    if not entries:
        base = section.split("(")[0]
        if base != section:
            entries = index.get(f"{act}:{base}", [])
    end = offset + min(limit, 100)
    return entries[offset:end]


# ---------------------------------------------------------------------------
# Citations (cases / rulings per section)
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def _load_citation_index() -> dict[str, dict[str, list[dict]]]:
    path = DATA_DIR / "citation_index.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def get_cases_for_section(act: str, section: str, limit: int = 50, offset: int = 0) -> list[dict]:
    act_data = _load_citation_index().get(act, {})
    entries = act_data.get(section, [])
    cases = [e for e in entries if e.get("type") == "case"]
    cases = [c for c in cases if classify_case(c.get("title", "")) == "tax"]
    end = offset + min(limit, 100)
    return cases[offset:end]


def get_rulings_for_section(act: str, section: str, limit: int = 50, offset: int = 0) -> list[dict]:
    act_data = _load_citation_index().get(act, {})
    entries = act_data.get(section, [])
    rulings = [e for e in entries if e.get("type") == "ruling"]
    end = offset + min(limit, 100)
    return rulings[offset:end]


# ---------------------------------------------------------------------------
# Smart links
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def _load_smartlink_index() -> dict[str, Any]:
    path = DATA_DIR / "smartlink_index.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    logger.warning("smartlink_index.json not found")
    return {}


def get_smartlinks_for_item(item_type: str, item_id: str) -> list[dict]:
    index = _load_smartlink_index()
    if item_type == "section":
        try:
            act_code, section_id = item_id.split("#")
            return index.get("sections", {}).get(act_code, {}).get(section_id, [])
        except ValueError:
            logger.error("Invalid section item_id format: %s", item_id)
            return []
    elif item_type == "case":
        return index.get("cases", {}).get(item_id, [])
    elif item_type == "ruling":
        return index.get("rulings", {}).get(item_id, [])
    elif item_type == "part":
        try:
            act_code, part_id = item_id.split("#")
            return index.get("parts", {}).get(act_code, {}).get(part_id, [])
        except ValueError:
            logger.error("Invalid part item_id format: %s", item_id)
            return []
    return []


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

TAX_KEYWORDS = ["commissioner of taxation", "federal commissioner of taxation",
                "deputy commissioner of taxation", r"\btax\b", "income tax", "gst"]
ASIC_KEYWORDS = ["australian securities and investments commission",
                 "australian securities commission", r"\basic\b"]


def classify_case(case_name: str) -> str:
    name = case_name.lower()
    is_tax = any(re.search(p, name) for p in TAX_KEYWORDS)
    is_asic = any(re.search(p, name) for p in ASIC_KEYWORDS)
    if is_tax and is_asic:
        return "asic"
    if is_tax:
        return "tax"
    if is_asic:
        return "asic"
    return "other"


def short_case_name(case_name: str) -> str:
    name = case_name.removeprefix("Re ")
    parts = re.split(r'\s+[vV]\s+', name, maxsplit=1)
    if len(parts) == 2:
        left, right = parts[0], parts[1]
        gov = ["commissioner", "commission", "asic", "australian securities",
               "director", "attorney-general", "minister", "administrator"]
        left_gov = any(k in left.lower() for k in gov)
        right_gov = any(k in right.lower() for k in gov)
        if left_gov and not right_gov:
            candidate = right
        elif right_gov and not left_gov:
            candidate = left
        else:
            candidate = left if len(left) < len(right) else right
    else:
        candidate = name
    candidate = re.split(r'[;,]\s+(In the Matter of|in the matter of|Receiver)', candidate)[0]
    candidate = re.split(r'\s+\(', candidate)[0]
    candidate = candidate.strip()
    company_indicators = ['pty ltd', 'ltd', 'limited', 'inc', 'corp', 'corporation',
                          'llc', 'plc', 'group', 'holdings', 'trustee', 'trust',
                          'superannuation', 'nominees']
    is_company = any(ind in candidate.lower() for ind in company_indicators)
    words = candidate.split()
    if not is_company and len(words) >= 2:
        return words[-1]
    return candidate


@functools.lru_cache(maxsize=None)
def load_cases() -> list[dict]:
    cases = []
    for f in sorted(CASE_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            case_name = data.get("case_name", "Unknown")
            cases.append({
                "citation": data.get("citation", f.stem),
                "title": case_name,
                "short_name": short_case_name(case_name),
                "category": classify_case(case_name),
                "court": data.get("court", ""),
                "year": data.get("year", 0),
                "date": data.get("decision_date", ""),
                "source_url": data.get("source_url", ""),
            })
        except Exception:
            logger.exception("Error loading case %s", f.name)
    return cases


# ---------------------------------------------------------------------------
# Rulings
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def load_rulings() -> list[dict]:
    rulings = []
    for f in sorted(RULING_DIR.glob("*.txt")):
        if f.name.endswith(".meta.json"):
            continue
        try:
            meta_path = f.with_suffix(f.suffix + ".meta.json")
            if not meta_path.exists():
                meta_path = f.parent / (f.stem + ".txt.meta.json")
            title = f.stem
            year = 0
            ruling_type = "LCG"
            m = re.match(r'^([A-Za-z]+)_(\d{4})_(\d+)', f.stem)
            if m:
                ruling_type = m.group(1).upper()
                year = int(m.group(2))
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                title = meta.get("title", title)
                ruling_type = meta.get("ruling_type") or meta.get("type") or ruling_type
                year = meta.get("year") or 0
                if meta.get("issue_date"):
                    dm = re.search(r'(\d{4})', str(meta.get("issue_date")))
                    if dm:
                        year = int(dm.group(1))
            content = f.read_text(encoding="utf-8")
            rulings.append({
                "citation": f.stem,
                "title": title,
                "type": ruling_type,
                "year": year,
                "source": str(f),
                "preview": content[:500],
            })
        except Exception:
            logger.exception("Error loading ruling %s", f.name)
    for subdir in ["td", "tr", "pcg", "ps_la"]:
        p = ATO_RULING_DIR / subdir
        if not p.exists():
            continue
        for f in sorted(p.glob("*.txt")):
            try:
                content = f.read_text(encoding="utf-8")
                lines = content.splitlines()
                title = lines[0].strip() if lines else f.stem
                year_match = re.search(r'(\d{4})', f.stem)
                year = int(year_match.group(1)) if year_match else 0
                rulings.append({
                    "citation": f.stem,
                    "title": title,
                    "type": subdir.upper().replace('_', ' '),
                    "year": year,
                    "source": str(f),
                    "preview": content[:500],
                })
            except Exception:
                logger.exception("Error loading ATO ruling %s", f.name)
    return rulings


@functools.lru_cache(maxsize=None)
def _load_ruling_section_index() -> dict[str, list[dict]]:
    path = DATA_DIR / "ruling_section_index.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def load_ruling_section_refs(citation: str) -> list[dict]:
    return _load_ruling_section_index().get(citation, [])


# ---------------------------------------------------------------------------
# Paragraph index
# ---------------------------------------------------------------------------

def slugify_cch(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text).strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s[:80]


@functools.lru_cache(maxsize=None)
def _load_paragraph_index() -> dict[str, dict]:
    paragraph_index: dict[str, dict] = {}
    for filename, pub_id in PUB_ACT_MAP.items():
        path = COMMENTARY_DIR / filename
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for ch in data.get("chapters", []):
            for mh in ch.get("major_headings", []):
                para = mh.get("paragraph_number", "")
                heading = mh.get("title", "")
                sec_id = slugify_cch(heading) or f"ch-{ch.get('number', '')}-{len(paragraph_index)}"
                if para:
                    key = f"{pub_id}:{para}"
                    paragraph_index[key] = {
                        "act": pub_id,
                        "section": sec_id,
                        "title": heading,
                        "chapter": ch.get("number"),
                        "paragraph": para,
                    }
                for sh in mh.get("sub_headings", []):
                    sh_para = sh.get("paragraph_number", "")
                    if sh_para:
                        key = f"{pub_id}:{sh_para}"
                        paragraph_index[key] = {
                            "act": pub_id,
                            "section": sec_id,
                            "title": sh.get("title", heading),
                            "chapter": ch.get("number"),
                            "paragraph": sh_para,
                        }
    return paragraph_index


def get_paragraph_info(pub_id: str, para: str) -> dict | None:
    key = f"{pub_id}:{para}"
    return _load_paragraph_index().get(key)


# ---------------------------------------------------------------------------
# Section content
# ---------------------------------------------------------------------------

def find_section_path(act: str, section: str) -> str | None:
    tree = load_tree(act)
    for part in tree.get("parts", []):
        for sec in part.get("sections", []):
            if sec["id"].lower() == section.lower():
                return sec["path"]
        for div in part.get("divisions", []):
            for sec in div.get("sections", []):
                if sec["id"].lower() == section.lower():
                    return sec["path"]
            for sub in div.get("subdivisions", []):
                for sec in sub.get("sections", []):
                    if sec["id"].lower() == section.lower():
                        return sec["path"]
    return None


def get_act_section_content(act: str, section: str) -> tuple[dict, str]:
    section_path = find_section_path(act, section)
    # If no exact match in tree, try case-insensitive glob for markdown file
    if not section_path:
        for md in (DATA_DIR / act / "sections").rglob("*.md"):
            if md.stem.lower() == section.lower():
                section_path = str(md.relative_to(DATA_DIR / act / "sections"))
                break

    # If still no section_path, the section is not in the tree at all
    if not section_path:
        raise HTTPException(status_code=404, detail=f"Section {section} not found")

    md_path = DATA_DIR / act / "sections" / section_path
    if not md_path.exists():
        # This case handles when section_path was found via find_section_path (exact/case-insensitive),
        # but for some reason the file it pointed to doesn't exist.
        # Given find_section_path should point to existing files *or* we handled above for tree-only,
        # this might indicate a data inconsistency. For now, treat as tree-only.
        logger.warning("Section file '%s' expected at path '%s' not found. Returning empty content.", section, md_path)
        return {}, ""


    content = md_path.read_text(encoding="utf-8")
    fm = {}
    body = content
    if content.startswith("---"):
        fm_end = re.search(r'\n---\s*\n', content)
        if fm_end:
            fm_text = content[3:fm_end.start()].strip()
            for line in fm_text.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip().strip('"')
            body = content[fm_end.end():]

    return fm, body


def get_definition_text(act: str, term: str) -> dict | None:
    defs = load_definitions(act)
    if not defs:
        return None
    info = defs.get(term.lower())
    if not info:
        return None
    section = info.get("section", "")
    if not section:
        return None

    sections_dir = DATA_DIR / act / "sections"
    md_path = None
    for f in sections_dir.rglob(f"{section}.md"):
        md_path = f
        break
    if not md_path:
        return None

    content = md_path.read_text(encoding="utf-8")
    if content.startswith("---"):
        fm_end = re.search(r"\n---\s*\n", content)
        body = content[fm_end.end():] if fm_end else content
    else:
        body = content

    term_lower = term.lower()
    idx = body.lower().find(term_lower)
    if idx == -1:
        return None

    end_pos = len(body)
    all_terms = sorted(defs.keys(), key=len, reverse=True)
    for t in all_terms:
        if t == term_lower:
            continue
        search_start = idx + len(term_lower)
        t_idx = body.lower().find(t, search_start)
        if t_idx != -1 and t_idx < end_pos:
            preceding = body[max(0, t_idx - 20):t_idx]
            if t_idx == 0 or body[t_idx - 1] in ".;:\n" or re.search(r"[.;:]\s*$", preceding) or re.search(r"\n\s*$", preceding):
                end_pos = t_idx

    text = body[idx:end_pos].strip()
    text = re.sub(r'<a id="[^"]+"></a>\s*\n?', "", text)
    text = re.sub(r">\s*", "", text)
    text = re.sub(r"\*\*\((\d+)\)\*\*\s*", r"(\1) ", text)
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"\n{2,}", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > 500:
        text = text[:497] + "..."

    return {
        "term": info.get("term", term),
        "act": act,
        "section": section,
        "anchor": info.get("anchor", ""),
        "text": text,
        "path": f"/{act}/s{section}#{info.get('anchor', '')}",
    }
