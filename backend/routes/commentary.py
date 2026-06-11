from __future__ import annotations

import logging
import re

from fastapi import APIRouter

from backend.services.data_loader import (
    get_commentary_for_section,
    get_smartlinks_for_item,
    get_act_section_content,
    load_tree,
    load_definitions,
)
from .cases import get_title_for_item

logger = logging.getLogger(__name__)
router = APIRouter()

# Mapping for cross-act references: full act name (lowercase) to its ID
ACT_NAME_TO_ID = {
    "income tax assessment act 1997": "itaa-1997",
    "income tax assessment act 1936": "itaa-1936",
    "fringe benefits tax assessment act 1986": "fbtaa-1986",
    "superannuation industry (supervision) act 1993": "sis-1993",
    "taxation administration act 1953": "taa-1953",
    "income tax assessment regulation 1997": "itar-1997",
    "a new tax system (goods and services tax) act 1999": "gst-1999",
    "goods and services tax act 1999": "gst-1999",
}


def _clean_markdown_for_analysis(text: str) -> str:
    """Remove code blocks and existing markdown links to prevent false positives."""
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", "", text)
    return text


@router.get("/api/commentary/{act}/{section}")
def get_commentary(act: str, section: str, limit: int = 50, offset: int = 0):
    entries = get_commentary_for_section(act, section, limit, offset)
    return {
        "act": act,
        "section": section,
        "count": len(entries),
        "commentary": entries,
    }


@router.get("/api/smart-links/{item_type}/{item_id:path}")
def get_smart_links(item_type: str, item_id: str):
    if item_type in ("section", "part"):
        item_id = item_id.replace("/", "#")

    links = get_smartlinks_for_item(item_type, item_id)

    links_with_titles = []
    for link in links:
        link_type = link.get("type")
        link_id = link.get("id")
        if link_type and link_id:
            title = get_title_for_item(link_type, link_id)
            links_with_titles.append({**link, "title": title})
        else:
            links_with_titles.append(link)

    return {
        "item_type": item_type,
        "item_id": item_id,
        "links": links_with_titles,
    }


@router.get("/api/section-refs/{act}/{section}")
def get_section_references(act: str, section: str):
    try:
        fm, body = get_act_section_content(act, section)
    except Exception:
        return {"act": act, "section": section, "sections": [], "definitions": []}

    if not body:
        return {"act": act, "section": section, "sections": [], "definitions": []}

    cleaned = _clean_markdown_for_analysis(body)
    current_upper = section.upper()

    # 1. Same-act section references
    same_act_refs: set[str] = set()

    # "section 8-1", "sections 6-5 and 6-10", "subsection 70-45"
    for m in re.finditer(
        r"(?:section|sections|subsection|subsections)\s+(\d+[A-Z]*[-\d]*)",
        cleaned,
        re.IGNORECASE,
    ):
        ref_id = m.group(1).strip().upper()
        if ref_id != current_upper:
            same_act_refs.add(ref_id)

    # Shorthand "s 8-1" — ensure 's' is standalone
    for m in re.finditer(
        r"(?<!\w)s\s+(\d+[A-Z]*[-\d]*)",
        cleaned,
        re.IGNORECASE,
    ):
        ref_id = m.group(1).strip().upper()
        if ref_id != current_upper:
            same_act_refs.add(ref_id)

    # 2. Cross-act references
    cross_act_refs: set[tuple[str, str]] = set()
    for m in re.finditer(
        r"(?:section|sections|subsection|subsections|\bs)\s+(\d+[A-Z]*[-\d]*)\s+of\s+the\s+([A-Za-z\s()]+Act\s+\d{4})",
        cleaned,
        re.IGNORECASE,
    ):
        ref_section = m.group(1).strip().upper()
        full_name = m.group(2).strip().lower()
        ref_act = ACT_NAME_TO_ID.get(full_name)
        if ref_act and (ref_act != act or ref_section != current_upper):
            cross_act_refs.add((ref_act, ref_section))

    # 3. Definition terms — look in raw body (not cleaned) so asterisks are intact
    definitions = load_definitions(act)
    found_definitions: dict[str, dict] = {}
    for m in re.finditer(r"\*([^*\n]+?)\*", body):
        term = m.group(1).strip()
        key = term.lower()
        if key in definitions and key not in found_definitions:
            info = definitions[key]
            found_definitions[key] = {
                "term": term,
                "section": info.get("section", ""),
                "anchor": info.get("anchor", ""),
                "title": info.get("title", term),
            }

    # 4. Build result with titles
    all_sections: list[dict] = []
    for ref_id in sorted(same_act_refs):
        title = get_title_for_item("section", f"{act}#{ref_id}")
        all_sections.append({"id": ref_id, "act": act, "title": title})

    for ref_act, ref_section in sorted(cross_act_refs):
        title = get_title_for_item("section", f"{ref_act}#{ref_section}")
        all_sections.append({"id": ref_section, "act": ref_act, "title": title})

    return {
        "act": act,
        "section": section,
        "sections": all_sections,
        "definitions": list(found_definitions.values()),
    }
