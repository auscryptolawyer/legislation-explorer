#!/usr/bin/env python3
"""
Build a citation index mapping legislation sections to cases and rulings that cite them.

Scans:
- cases: /home/harrison/projects/asic-scraper/cases_filtered_v2/*.json
- rulings: /home/harrison/projects/cadena-knowledge-MCP/data/rulings/*.txt
- ato_rulings: /home/harrison/projects/cadena-knowledge-MCP/data/ato_rulings/td/*.txt, tr/*.txt

Outputs:
- data/citation_index.json  { act: { section: [ { type, citation, title, year, snippet } ] } }
"""

import json
import re
import os
from pathlib import Path
from collections import defaultdict

CASE_DIR = Path("/home/harrison/projects/asic-scraper/cases_filtered_v2")
RULING_DIR = Path("/home/harrison/projects/cadena-knowledge-MCP/data/rulings")
ATO_RULING_DIR = Path("/home/harrison/projects/cadena-knowledge-MCP/data/ato_rulings")
DATA_DIR = Path("/home/harrison/legislation-explorer/data")
OUT_PATH = DATA_DIR / "citation_index.json"

# Load known sections per act to disambiguate
KNOWN_SECTIONS = {}
for act_dir in DATA_DIR.iterdir():
    if not act_dir.is_dir():
        continue
    sections_dir = act_dir / "sections"
    if not sections_dir.exists():
        continue
    section_ids = set()
    for f in sections_dir.rglob("*.md"):
        section_ids.add(f.stem)
    if section_ids:
        KNOWN_SECTIONS[act_dir.name] = section_ids

print(f"Known sections per act:")
for act, secs in KNOWN_SECTIONS.items():
    print(f"  {act}: {len(secs)} sections")

# Section citation regexes
SECTION_RE = re.compile(
    r"(?:s\s*\.?\s*|section\s+)"
    r"(\d+[A-Z]*(?:-\d+)?)"
    r"(?:\s*\(\s*\d+[A-Z]*\s*\)(?:\s*\([a-z]\))?)?",
    re.IGNORECASE,
)

# Also match "ss 8-1(1)" etc
PLURAL_SECTION_RE = re.compile(
    r"ss\s+([\d\-A-Z]+(?:\s*,\s*[\d\-A-Z]+)+)",
    re.IGNORECASE,
)

# Division references
DIVISION_RE = re.compile(
    r"(?:Division|Div)\s+(\d+[A-Z]*)",
    re.IGNORECASE,
)

# Act name hints near citations
ACT_HINT_RE = re.compile(
    r"(?:ITAA\s*(?:19)?97|Income\s+Tax\s+Assessment\s+Act\s+1997)"
    r"|(?:ITAA\s*1936|Income\s+Tax\s+Assessment\s+Act\s+1936)"
    r"|(?:GST\s+Act|A\s*New\s+Tax\s+System\s*\(?Goods\s+and\s+Services\s+Tax\)?\s*Act)"
    r"|(?:TAA\s*1953|Taxation\s+Administration\s+Act\s+1953)"
    r"|(?:FBT\s+Act|Fringe\s+Benefits\s+Tax\s+Assessment\s+Act)"
    r"|(?:SIS\s+Act|Superannuation\s+Industry\s+Supervision\s+Act)",
    re.IGNORECASE,
)


def extract_sections(text: str) -> list[tuple[str, str | None]]:
    """Extract (section_id, act_hint) pairs from text."""
    results = []
    for m in SECTION_RE.finditer(text):
        sec = m.group(1)
        # Look back 200 chars for act hint
        start = max(0, m.start() - 200)
        context = text[start:m.start()]
        act_hint = None
        hint_match = ACT_HINT_RE.search(context)
        if hint_match:
            hint = hint_match.group(0).lower()
            if "1997" in hint or "itaa 97" in hint:
                act_hint = "itaa-1997"
            elif "1936" in hint or "itaa 1936" in hint:
                act_hint = "itaa-1936"
            elif "gst" in hint:
                act_hint = "gst-1999"
            elif "taxation administration" in hint or "taa" in hint:
                act_hint = "taa-1953"
            elif "fringe benefits" in hint or "fbt" in hint:
                act_hint = "fbt-1986"
            elif "superannuation" in hint or "sis" in hint:
                act_hint = "sis-1993"
        results.append((sec, act_hint))
    return results


def resolve_act(section_id: str, act_hint: str | None) -> str | None:
    """Map a section ID to an act ID."""
    if act_hint and act_hint in KNOWN_SECTIONS:
        if section_id in KNOWN_SECTIONS[act_hint]:
            return act_hint

    # Try all acts, prefer ITAA 1997 for hyphenated sections
    candidates = []
    for act_id, secs in KNOWN_SECTIONS.items():
        if section_id in secs:
            candidates.append(act_id)

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    # Disambiguation heuristics
    if "-" in section_id:
        # Hyphenated sections are ITAA 1997 or TAA 1953 or GST
        if "itaa-1997" in candidates:
            return "itaa-1997"
        if "taa-1953" in candidates:
            return "taa-1953"
        if "gst-1999" in candidates:
            return "gst-1999"
    else:
        # Non-hyphenated are mostly ITAA 1936 or old ITAA 1997 sections
        if "itaa-1936" in candidates:
            return "itaa-1936"
        if "itaa-1997" in candidates:
            return "itaa-1997"

    return candidates[0]


def build_case_index() -> dict:
    index = defaultdict(lambda: defaultdict(list))
    case_files = list(CASE_DIR.glob("*.json"))
    print(f"\nScanning {len(case_files)} cases...")

    for i, case_file in enumerate(case_files):
        if i % 100 == 0:
            print(f"  {i}/{len(case_files)}")
        try:
            with open(case_file) as f:
                case = json.load(f)
        except Exception as e:
            print(f"  Skip {case_file.name}: {e}")
            continue

        content = case.get("content", "")
        citation = case.get("citation", case_file.stem)
        case_name = case.get("case_name", "Unknown")
        year = case.get("year", 0)
        court = case.get("court", "")

        # Extract sections
        seen = set()
        for sec, hint in extract_sections(content):
            act = resolve_act(sec, hint)
            if not act:
                continue
            key = (act, sec)
            if key in seen:
                continue
            seen.add(key)

            # Get a snippet around the first mention
            m = re.search(rf"(?:s\s*\.?\s*|section\s+){re.escape(sec)}", content, re.IGNORECASE)
            snippet = ""
            if m:
                start = max(0, m.start() - 120)
                end = min(len(content), m.end() + 120)
                snippet = content[start:end].replace("\n", " ").strip()

            index[act][sec].append({
                "type": "case",
                "citation": citation,
                "title": case_name,
                "year": year,
                "court": court,
                "snippet": snippet,
            })

    return index


def build_ruling_index(index: dict) -> dict:
    ruling_files = list(RULING_DIR.glob("*.txt"))
    # Also scan ato_rulings subdirs
    if ATO_RULING_DIR.exists():
        for subdir in ["td", "tr", "pcg", "ps_la"]:
            p = ATO_RULING_DIR / subdir
            if p.exists():
                ruling_files.extend(p.glob("*.txt"))

    print(f"\nScanning {len(ruling_files)} rulings...")

    for i, ruling_file in enumerate(ruling_files):
        if i % 50 == 0:
            print(f"  {i}/{len(ruling_files)}")
        try:
            with open(ruling_file) as f:
                content = f.read()
        except Exception as e:
            print(f"  Skip {ruling_file.name}: {e}")
            continue

        # Try to load meta
        meta_path = ruling_file.with_suffix(ruling_file.suffix + ".meta.json")
        if not meta_path.exists():
            meta_path = ruling_file.parent / (ruling_file.stem + ".txt.meta.json")
        title = ruling_file.stem
        ruling_type = "ruling"
        year = 0
        if meta_path.exists():
            try:
                with open(meta_path) as f:
                    meta = json.load(f)
                title = meta.get("title", title)
                year = meta.get("year", 0)
                ruling_type = meta.get("type", "ruling")
            except Exception:
                pass

        seen = set()
        for sec, hint in extract_sections(content):
            act = resolve_act(sec, hint)
            if not act:
                continue
            key = (act, sec, ruling_file.name)
            if key in seen:
                continue
            seen.add(key)

            m = re.search(rf"(?:s\s*\.?\s*|section\s+){re.escape(sec)}", content, re.IGNORECASE)
            snippet = ""
            if m:
                start = max(0, m.start() - 120)
                end = min(len(content), m.end() + 120)
                snippet = content[start:end].replace("\n", " ").strip()

            index[act][sec].append({
                "type": "ruling",
                "citation": ruling_file.stem,
                "title": title,
                "year": year,
                "ruling_type": ruling_type,
                "snippet": snippet,
            })

    return index


def main():
    index = build_case_index()
    index = build_ruling_index(index)

    # Convert to plain dict
    out = {}
    total_refs = 0
    for act, sections in index.items():
        out[act] = {}
        for sec, refs in sections.items():
            out[act][sec] = refs
            total_refs += len(refs)

    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)

    print(f"\nDone. Wrote {OUT_PATH}")
    print(f"  Acts: {len(out)}")
    print(f"  Total section references: {total_refs}")
    for act, secs in out.items():
        print(f"  {act}: {len(secs)} sections cited")


if __name__ == "__main__":
    main()
