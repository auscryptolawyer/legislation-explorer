#!/usr/bin/env python3
"""
Extract defined terms from ITAA 1997 (s995-1) and ITAA 1936 (s6) definition sections.
Outputs data/definitions.json
"""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path.home() / "legislation-explorer"
DATA_DIR = BASE / "data"
OUT_PATH = DATA_DIR / "definitions.json"

PREDICATE_RE = re.compile(
    r"([A-Za-z0-9\-'%][A-Za-z0-9\-'% ]{0,60}?)\s+"
    r"(has the meaning given by|means|has the same meaning as in|includes|has the meaning affected by)",
    re.IGNORECASE,
)

ANCHOR_RE = re.compile(r'<a id="([^"]+)">')

FALSE_STARTS = {
    "The ", "This ", "Note:", "Section ", "Division ", "Part ",
    "For ", "If ", "It ", "There ", "Subject ", "Without ",
}

# Allow "A " and "An " only if the term is exactly "A" or "An"
FALSE_STARTS_EXACT = {"A ", "An "}


def is_false_positive(term: str) -> bool:
    t = term.strip()
    if not t:
        return True
    # Filter terms starting with obvious false positives
    for prefix in FALSE_STARTS:
        if t.startswith(prefix):
            return True
    for prefix in FALSE_STARTS_EXACT:
        if t.startswith(prefix) and t != prefix.strip():
            return True
    # Filter terms containing "subsection" or "section" unless legitimate
    lowered = t.lower()
    if "subsection" in lowered or " section" in lowered:
        # Allow if it looks like a legitimate term with numbers
        # e.g., "95% services indirect value shift"
        # A simple heuristic: if it contains a % sign or looks like a specific term
        if "%" not in t and not re.search(r"\d", t):
            return True
        # Additional check: if it literally just contains "section" or "subsection" as a word
        words = lowered.split()
        if "section" in words or "subsection" in words:
            return True
    return False


def extract_from_file(md_path: Path, act: str, section: str) -> dict:
    content = md_path.read_text(encoding="utf-8")

    # Find all anchors with their positions
    anchors = []
    for m in ANCHOR_RE.finditer(content):
        anchors.append((m.start(), m.group(1)))

    # We only care about subsection (1). Find its bounds.
    # Match the line that starts with <a id="..."> and **(1)**
    subsection_1_start = None
    for m in re.finditer(r'^(<a id="[^"]+"></a>\n)?\*\*\(1\)\*\*', content, re.MULTILINE):
        subsection_1_start = m.start()
        break

    if subsection_1_start is None:
        raise ValueError(f"Could not find subsection (1) in {md_path}")

    # Find next subsection like **(2)** or end of content
    next_sub = re.search(r'\n\*\*\(\d+\)\*\*', content[m.end():])
    if next_sub:
        subsection_1_end = m.end() + next_sub.start()
    else:
        subsection_1_end = len(content)

    subsection_text = content[m.start():subsection_1_end]

    terms: dict[str, dict] = {}
    seen: set[str] = set()

    for m in PREDICATE_RE.finditer(subsection_text):
        term = m.group(1).strip()
        if is_false_positive(term):
            continue

        # Deduplicate case-insensitively but keep original casing
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)

        # Find nearest anchor BEFORE this term in the FULL file
        abs_term_start = subsection_1_start + m.start()
        anchor = None
        for pos, aid in anchors:
            if pos < abs_term_start:
                anchor = aid
            else:
                break

        terms[term] = {"anchor": anchor}

    return {
        "section": section,
        "terms": terms,
    }


def main():
    catalog = {}

    catalog["itaa-1997"] = extract_from_file(
        DATA_DIR / "itaa-1997" / "sections" / "part-6-5" / "division-995" / "995-1.md",
        "itaa-1997",
        "995-1",
    )

    catalog["itaa-1936"] = extract_from_file(
        DATA_DIR / "itaa-1936" / "sections" / "part-i" / "division-unknown" / "6.md",
        "itaa-1936",
        "6",
    )

    OUT_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")

    total_terms = sum(len(v["terms"]) for v in catalog.values())
    print(f"Extracted {total_terms} terms across {len(catalog)} acts.")
    for act, info in catalog.items():
        print(f"  {act}: {len(info['terms'])} terms (section {info['section']})")


if __name__ == "__main__":
    main()
