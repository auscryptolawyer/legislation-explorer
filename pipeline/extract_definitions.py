"""
extract_definitions.py — Parse ITAA 1997 section 995-1 and ITAA 1936 section 6

Outputs:
  - data/{act}/definitions.json          (ITAA 1997: 995-1 terms)
  - data/{act}/definitions-s6.json       (ITAA 1936: s6(1) terms)
  - data/{act}/definitions-local.json    (ITAA 1936: local Part/Division defs)
  - Rewrites the source section markdown with per-definition anchors.

Usage:
    python3 pipeline/extract_definitions.py --act itaa-1997
    python3 pipeline/extract_definitions.py --act itaa-1936
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    """Lowercase, hyphenate, strip punctuation."""
    s = text.lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    return s


def strip_noise(lines: list[str]) -> list[str]:
    """Remove page headers, footers, compilation lines from raw 995-1 text."""
    cleaned: list[str] = []
    skip_patterns = [
        re.compile(r"^\s*Income Tax Assessment Act 1997\s*\d+\s*$"),
        re.compile(r"^\s*Compilation No\."),
        re.compile(r"^\s*Compilation date:"),
        re.compile(r"^\s*Authorised Version"),
        re.compile(r"^\s*Registered:"),
        re.compile(r"^_{3,}$"),
        re.compile(r"^\*To find definitions of asterisked terms"),
        re.compile(r"^\s*The Dictionary Chapter 6\s*$"),
        re.compile(r"^\s*Dictionary definitions Part 6-5\s*$"),
        re.compile(r"^\s*Definitions Division 995\s*$"),
        re.compile(r"^\s*Section 995-1\s*$"),
        re.compile(r"^\s*Chapter 6 The Dictionary\s*$"),
        re.compile(r"^\s*Part 6-5 Dictionary definitions\s*$"),
        re.compile(r"^\s*Division 995 Definitions\s*$"),
        re.compile(r"^\s*\d+\s+Income Tax Assessment Act 1997\s*\d+\s*$"),
    ]
    for line in lines:
        stripped = line.rstrip("\n\r")
        # Remove form feed
        stripped = stripped.replace("\f", "")
        if not stripped.strip():
            cleaned.append("")
            continue
        skip = False
        for pat in skip_patterns:
            if pat.match(stripped):
                skip = True
                break
        if not skip:
            cleaned.append(stripped)
    return cleaned


def is_structural_marker(line: str) -> bool:
    """Paragraph, subparagraph, or note markers within a definition."""
    stripped = line.strip()
    if re.match(r"^\(([a-z]{1,3})\)\s", stripped):
        return True
    if re.match(r"^\(([ivx]+)\)\s", stripped):
        return True
    if stripped.startswith("Note:") or stripped.startswith("Note "):
        return True
    return False


def contains_headword_pattern(line: str) -> bool:
    """True if this line contains a definition headword marker."""
    stripped = line.strip()
    if "has the meaning given by" in stripped:
        return True
    if re.search(r"\bmeans\b", stripped):
        return True
    # Colon headword: colon must appear reasonably early and not be part of a sentence
    # Heuristic: colon before position 120, and text before colon doesn't end with a sentence-ending punctuation
    if ":" in stripped:
        idx = stripped.find(":")
        if 0 < idx < 120:
            before = stripped[:idx].strip()
            # Reject if before-colon text ends with period/question mark (sentence with colon)
            if before and before[-1] not in ".?":
                return True
    return False


def extract_term_from_line(line: str) -> str | None:
    """Given a line known to contain a headword pattern, extract the term."""
    stripped = line.strip()
    for marker in ["has the meaning given by", " means "]:
        if marker in stripped:
            return stripped.split(marker, 1)[0].strip()
    if ":" in stripped:
        idx = stripped.find(":")
        return stripped[:idx].strip()
    return None


def parse_9951_definitions(raw_lines: list[str]) -> list[dict]:
    """
    Walk the cleaned raw lines of 995-1 and extract defined terms.
    Uses a single-pass line-by-line approach.
    """
    defs: list[dict] = []
    current_term: str | None = None
    current_lines: list[str] = []

    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        if not line.strip():
            if current_term:
                current_lines.append("")
            i += 1
            continue

        leading = len(line) - len(line.lstrip())
        stripped = line.strip()

        # Structural markers always belong to the current definition
        if is_structural_marker(line):
            if current_term:
                current_lines.append(stripped)
            i += 1
            continue

        # Potential new headword: must have significant indent and contain a pattern
        if leading >= 10 and contains_headword_pattern(line):
            term = extract_term_from_line(line)
            if term:
                # Save previous
                if current_term:
                    defs.append({
                        "term": current_term,
                        "text": " ".join(current_lines).strip(),
                        "slug": slugify(current_term),
                    })
                current_term = term
                current_lines = [stripped]
                i += 1
                continue

        # Everything else at significant indent is continuation of current definition
        if current_term and leading >= 10:
            current_lines.append(stripped)

        i += 1

    if current_term:
        defs.append({
            "term": current_term,
            "text": " ".join(current_lines).strip(),
            "slug": slugify(current_term),
        })

    return defs


def rewrite_9951_markdown(section_path: Path, defs: list[dict]) -> str:
    """
    Inject anchors into the existing 995-1 markdown.
    Strategy: prepend an anchor before each definition's first mention of the term.
    """
    content = section_path.read_text(encoding="utf-8")
    if content.startswith("---"):
        fm_end = content.find("---", 3)
        frontmatter = content[:fm_end + 3]
        body = content[fm_end + 3:]
    else:
        frontmatter = ""
        body = content

    for d in defs:
        term = d["term"]
        slug = d["slug"]
        anchor = f'<a id="s995-1-{slug}"></a>'
        esc = re.escape(term)
        pat = re.compile(r"\b" + esc + r"\b", re.IGNORECASE)
        body, count = pat.subn(anchor + term, body, count=1)
        if count == 0:
            body = pat.sub(anchor + term, body, count=1)

    return frontmatter + body


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--act", choices=["itaa-1997", "itaa-1936"], required=True)
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--raw-dir", type=Path, default=None)
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args()

    logging.basicConfig(level=args.log_level, format="%(message)s")

    base = Path.home() / "legislation-explorer"
    data_dir = args.data_dir or base / "data" / args.act
    raw_dir = args.raw_dir or base / "data" / args.act / "raw"

    if args.act == "itaa-1997":
        raw_file = raw_dir / "vol10.txt"
        if not raw_file.exists():
            logging.error("vol10.txt not found in %s", raw_dir)
            return

        with raw_file.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.read().split("\n")

        # Slice out 995-1 lines
        start_idx = None
        end_idx = None
        for i, line in enumerate(lines):
            if re.match(r"^995-1\s+Definitions", line):
                start_idx = i
            elif start_idx is not None and re.match(r"^995-5\s+", line):
                end_idx = i
                break

        if start_idx is None:
            logging.error("Could not find 995-1 in raw text")
            return
        if end_idx is None:
            end_idx = len(lines)

        raw_9951 = lines[start_idx:end_idx]
        cleaned = strip_noise(raw_9951)
        defs = parse_9951_definitions(cleaned)
        logging.info("Extracted %d definitions from 995-1", len(defs))

        definitions = {}
        for d in defs:
            key = d["term"].lower()
            # Avoid overwriting with duplicate keys (use first occurrence)
            if key not in definitions:
                definitions[key] = {
                    "term": d["term"],
                    "section": "995-1",
                    "anchor": f"s995-1-{d['slug']}",
                    "act": "ITAA 1997",
                }

        out_json = data_dir / "definitions.json"
        out_json.write_text(json.dumps(definitions, indent=2), encoding="utf-8")
        logging.info("Wrote %s (%d unique terms)", out_json, len(definitions))

        section_md = data_dir / "sections" / "part-6-5" / "division-995" / "995-1.md"
        if section_md.exists():
            new_md = rewrite_9951_markdown(section_md, defs)
            section_md.write_text(new_md, encoding="utf-8")
            logging.info("Rewrote %s with anchors", section_md)
        else:
            logging.warning("%s not found; skipping markdown rewrite", section_md)

    else:
        logging.info("ITAA 1936 definition extraction not yet implemented")


if __name__ == "__main__":
    main()
