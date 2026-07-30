from __future__ import annotations

import logging

from fastapi import HTTPException, APIRouter

from backend.config import DATA_DIR
from backend.services.data_loader import load_tree, get_act_section_content
from backend.processors.markdown import (
    link_definitions, format_definition_terms,
    link_section_references, link_cross_act_references, auto_link_definitions,
)

from .rulings import list_rulings, get_ruling
from .tax_cases import list_tax_cases_tree, get_tax_case_by_citation

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/acts")
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
    acts.append({"id": "rulings", "name": "ATO Rulings", "compilation_no": None, "compilation_date": None})
    acts.append({"id": "tax-cases", "name": "Tax Cases", "compilation_no": None, "compilation_date": None})
    return acts


@router.get("/api/tree/{act}")
def get_tree(act: str):
    if act == "rulings":
        return list_rulings()
    if act == "tax-cases":
        return list_tax_cases_tree()
    return load_tree(act)


@router.get("/api/section/{act}/{section:path}")
def get_section(act: str, section: str):
    if act == "rulings":
        return get_ruling(section)

    if act == "tax-cases":
        return get_tax_case_by_citation(section)

    fm, body = get_act_section_content(act, section)
    body = format_definition_terms(body, section, act)
    body = link_definitions(body, act)
    body = link_section_references(body, act)
    body = link_cross_act_references(body, act)
    body = auto_link_definitions(body, act, section)

    return {"frontmatter": fm, "body": body}
