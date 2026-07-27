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

# Ligature normalisation — some CCH content uses typographic ligatures
# (ﬃ, ﬁ, ﬀ) that don't render on all devices
_LIGATURE_TABLE = str.maketrans({
    '\ufb00': 'ff',   # ﬀ
    '\ufb01': 'fi',   # ﬁ
    '\ufb02': 'fl',   # ﬂ
    '\ufb03': 'ffi',  # ﬃ
    '\ufb04': 'ffl',  # ﬄ
    '\ufb05': 'st',   # ﬅ
    '\ufb06': 'st',   # ﬆ
})
def _normalise_text(s: str) -> str:
    return s.translate(_LIGATURE_TABLE)


_ATO_ID_HEADER = re.compile(
    r'^(ATO\s+Interpretative\s+Decision|ATO\s+ID\s+\d{4}/\d+|={3,}|'
    r'File\s+Number|FOI\s+status|This\s+ATO\s+ID|This\s+document)',
    re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Acts / sections
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def load_tree(act: str) -> dict:
    path = DATA_DIR / act / "tree.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Act {act} not found")
    tree = json.loads(path.read_text(encoding="utf-8"))
    # Normalise section titles
    for part in tree.get("parts", []):
        for sec in part.get("sections", []):
            sec["title"] = _normalise_text(sec["title"])
        for div in part.get("divisions", []):
            for sec in div.get("sections", []):
                sec["title"] = _normalise_text(sec["title"])
            for sub in div.get("subdivisions", []):
                for sec in sub.get("sections", []):
                    sec["title"] = _normalise_text(sec["title"])
                sub["title"] = _normalise_text(sub.get("title", ""))
            div["title"] = _normalise_text(div.get("title", ""))
        part["title"] = _normalise_text(part.get("title", ""))
    return tree


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
                        "chapter_title": _normalise_text(ch.get("title", "")),
                        "heading_title": _normalise_text(mh.get("title", "")),
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
            m = re.match(r'^([A-Za-z]+)_(\d{2,4})_(\d+)', f.stem)
            if m:
                ruling_type = m.group(1).upper()
                # Normalize PSLA → PS LA for display consistency
                if ruling_type == "PSLA":
                    ruling_type = "PS LA"
                year = int(m.group(2))
                # Normalise 2-digit years (98 → 1998, 04 → 2004)
                if year < 100:
                    year += 1900 if year >= 90 else 2000
            else:
                # Single-number format: IT_262, SGR_2006_1, etc.
                m2 = re.match(r'^([A-Za-z]+)_(\d+)$', f.stem)
                if m2:
                    ruling_type = m2.group(1).upper()
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                title = meta.get("title", title)
                ruling_type = meta.get("ruling_type") or meta.get("type") or ruling_type
                if meta.get("year"):
                    year = int(meta["year"])
                if meta.get("issue_date"):
                    dm = re.search(r'(\d{4})', str(meta.get("issue_date")))
                    if dm:
                        year = int(dm.group(1))
            content = f.read_text(encoding="utf-8")
            # Extract descriptive title from content (line after the ruling citation)
            full_title = title
            # Strip ATO ID header lines before extracting title
            content_for_title = content
            if ruling_type == "PS LA" or ruling_type == "AID":
                # Remove known header lines
                ct_lines = content.splitlines()
                for ci, cl in enumerate(ct_lines):
                    if re.match(r'^(ATO\s+Interpretative\s+Decision|ATO\s+ID\s+\d{4}/\d+|=+)$', cl.strip(), re.IGNORECASE):
                        continue
                    if re.match(r'^(File\s+Number|FOI\s+status)', cl.strip(), re.IGNORECASE):
                        continue
                    if not cl.strip():
                        continue
                    content_for_title = '\n'.join(ct_lines[ci:])
                    break
            lines = content_for_title.splitlines()
            for i, ln in enumerate(lines):
                ln = ln.strip()
                # Find the citation line, take the next non-empty line as the title
                if re.match(r'^[A-Z]+ \\d{4}/\\d+', ln) or re.match(r'^\\w{2,4} \\d{4}/\\d+', ln) or re.match(r'^ATO ID \\d{4}/\\d+', ln) or re.match(r'^PS LA \\d{4}/\\d+', ln):
                    for j in range(i + 1, min(i + 10, len(lines))):
                        next_ln = lines[j].strip()
                        if not next_ln:
                            continue
                        # Skip known header/boilerplate lines
                        if re.match(r'^(Keywords|Date of decision|SUBJECT|PURPOSE|Paragraph|FOI status|Issue|Decision|Facts|CAUTION|Download|Email|Print|Back to browse|Contents)', next_ln, re.IGNORECASE):
                            continue
                        # Skip single-word category headers (e.g. "Excise", "Income Tax")
                        if re.match(r'^[A-Z][a-z]+( [A-Z][a-z]+)?$', next_ln.strip()):
                            # Check if the next line is indented (actual title) - if so, skip this category header
                            if j + 1 < len(lines) and lines[j + 1].startswith(' ') and lines[j + 1].strip():
                                continue
                        if next_ln and not next_ln.startswith("Please") and not next_ln.startswith("PDF") and not next_ln.startswith("This ATO ID") and not next_ln.startswith("This document") and not re.match(r'^[A-Z]+ \\d{4}/\\d+', next_ln) and not re.match(r'^={3,}', next_ln):
                            full_title = next_ln
                            break
                    break
            withdrawn = bool(re.search(r'\bwithdrawn\b', content[:1000], re.IGNORECASE))
            rulings.append({
                "citation": f.stem,
                "title": title,
                "full_title": full_title,
                "type": ruling_type,
                "year": year,
                "source": str(f),
                "preview": content[:500],
                "withdrawn": withdrawn,
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
                # Extract descriptive title: find the citation line, take next non-empty meaningful line
                full_title = title
                for i, ln in enumerate(lines):
                    ln = ln.strip()
                    if re.match(r'^[A-Z]+ \d{4}/\d+', ln) or re.match(r'^\w{2,4} \d{4}/\d+', ln):
                        for j in range(i + 1, min(i + 5, len(lines))):
                            next_ln = lines[j].strip()
                            if next_ln and not next_ln.startswith("Please") and not next_ln.startswith("PDF"):
                                full_title = next_ln
                                break
                        break
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

    # ── URL generators ────────────────────────────────────────────────────────
    _ato_doc_map = {
        "TR": "TXR",
        "TD": "TXD",
        "PCG": "COG",
        "LCG": "COG",
        "LCR": "COG",
        "PS LA": "ATOPSLA",
        "PS_LA": "ATOPSLA",
        "PSLA": "ATOPSLA",
        "GSTR": "GST",
        "MT": "MXR",
        "TA": "TPA",
        "SGR": "SGR",
        "AID": "AID",
    }

    def _ato_url(rtype: str, prefix: str, year: int | None, num: str) -> str | None:
        """Generate ATO URL — document viewer with PiT parameter.

        Format: law/view/document?DocID={code}/{prefix}{yr}{num}/NAT/ATO/00001&amp;PiT=99991231235958
        PiT=99991231235958 is the "latest point in time" parameter.
        Plain slashes work (no URL encoding needed).
        """
        if rtype == "IT":
            docid = f"ITR/IT{num}/NAT/ATO/00001"
        elif rtype == "AID":
            return f"https://www.ato.gov.au/law/view/document?docid=AID/AID{year}{num}/00001"
        else:
            code = _ato_doc_map.get(rtype)
            if not code:
                return None
            yr = str(year) if year else ""
            docid = f"{code}/{prefix}{yr}{num}/NAT/ATO/00001"
        return f"https://www.ato.gov.au/law/view/document?DocID={docid}&PiT=99991231235958"

    def _austlii_url(rtype: str, docid_num: str, year: int) -> str | None:
        ato_path_map = {
            "TR": f"ATOTR/{year}/TR{docid_num}.html",
            "TD": f"ATOTD/{year}/TD{docid_num}.html",
            "PCG": f"ATOPCG/{year}/PCG{docid_num}.html",
            "LCG": f"ATOLCG/{year}/LCG{docid_num}.html",
            "LCR": f"ATOLCR/{year}/LCR{docid_num}.html",
            "PS LA": None,
            "PS_LA": None,
        }
        path = ato_path_map.get(rtype)
        if not path:
            return None
        return f"https://www8.austlii.edu.au/au/other/rulings/ato/{path}"

    for r in rulings:
        parts = r["citation"].split("_", 2)
        if len(parts) == 3:
            rtype, yr_raw, num = parts
            # Handle PS LA citations: "PS"_"LA"_"2011_10" → type="PS_LA", yr=2011, num=10
            if rtype.upper() == "PS" and yr_raw.upper() == "LA":
                rtype = "PSLA"
                yr_doc_num = num.split("_", 1)
                yr_raw = yr_doc_num[0]
                num = yr_doc_num[1] if len(yr_doc_num) > 1 else yr_doc_num[0]
            yr = str(r["year"]) if r["year"] else yr_raw
            # Build the docid number part: <year><num> with correct year width
            if rtype == "PSLA":
                r["citation_display"] = f"PS LA {yr}/{num}"
            elif rtype == "AID":
                r["citation_display"] = f"ATO ID {yr}/{num}"
            else:
                r["citation_display"] = f"{rtype} {yr}/{num}"
            yr_doc = str(r["year"])[-2:] if r["year"] and r["year"] < 2000 else str(r["year"]) if r["year"] else yr_raw
            docid_num = f"{yr_doc}{num}"
            r["ato_url"] = _ato_url(r["type"], rtype, r.get("year"), num) or ""
            r["austlii_url"] = _austlii_url(r["type"], docid_num, r["year"]) or ""
        elif len(parts) == 2 and parts[0].upper() == "IT":
            # IT rulings: IT_262 — sequential numbering, no year
            rtype, num = parts
            r["citation_display"] = f"IT {num}"
            # ATO URL: plain DocID with PiT parameter
            r["ato_url"] = f"https://www.ato.gov.au/law/view/document?DocID=ITR/IT{num}/NAT/ATO/00001&PiT=99991231235958"
            r["austlii_url"] = ""
        else:
            r["citation_display"] = r["citation"]
            r["ato_url"] = ""
            r["austlii_url"] = ""

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
    content = _normalise_text(content)
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
    escaped = re.escape(term_lower)
    # Match: term followed by definition keywords anywhere in the body text
    # (?<!\w) ensures we don't match compound terms like "demerger dividend" for "dividend"
    # Patterns for definition anchors
    patterns = [
        rf'(?<!\w){escaped}\s+(?:has\s+(?:the\s+)?(?:same\s+)?meaning|means|includes)(?:\s|:|$)',
        rf'(?<!\w){escaped}\s*:',
    ]

    # Collect ALL matches so we can prefer the primary definition
    # over sub-definitions (e.g. prefer "dividend includes:" over
    # "demerger dividend means:...")
    candidates: list[tuple[re.Match, int]] = []
    for pat in patterns:
        for m in re.finditer(pat, body, re.IGNORECASE):
            # Determine if this is a primary definition by checking
            # whether the term is preceded by a sentence boundary
            # (start of content, newline, or ". ") rather than by
            # another word (which would indicate a compound term).
            before = body[max(0, m.start() - 60):m.start()].rstrip()
            is_primary = (
                m.start() == 0
                or before.endswith('.')
                or before.endswith('.\n')
                or before.endswith(';')
                or before.endswith('\n')
                or before.endswith(':')
                or not before
            )
            # Prefer earlier matches for primary; later matches for sub-definitions
            priority = 0 if is_primary else 1
            candidates.append((m, priority))

    if not candidates:
        return None

    # Sort: primary definitions first, then by position
    candidates.sort(key=lambda c: (c[1], c[0].start()))
    m = candidates[0][0]
    idx = m.start()

    # Find end: next col-0 line (start of next definition) or sentence boundary
    rest = body[idx + len(m.group()):]
    m2 = re.search(r'\n(?=[^\s>#<\-\d\[\(\*\'\`"])', rest)
    if m2:
        end_pos = idx + len(m.group()) + m2.start()
    else:
        m3 = re.search(r'\.\s+(?=[A-Z][a-z])', rest)
        if m3:
            end_pos = idx + len(m.group()) + m3.start() + 1
        else:
            end_pos = len(body)

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
