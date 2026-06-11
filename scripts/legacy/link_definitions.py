"""
link_definitions.py — Post-process markdown to hyperlink defined terms.

For ITAA 1997: looks up *term markers in definitions.json and links to s995-1.
For ITAA 1936: looks up local definitions first, then s6 fallback.

Usage:
    python3 pipeline/link_definitions.py --act itaa-1997
    python3 pipeline/link_definitions.py --act itaa-1936
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path


def load_definitions(data_dir: Path, act: str) -> dict[str, dict]:
    """Load the appropriate definition lookup table."""
    if act in ("itaa-1997", "gst-1999"):
        path = data_dir / "definitions.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    else:
        local = data_dir / "definitions-local.json"
        s6 = data_dir / "definitions-s6.json"
        defs = {}
        if s6.exists():
            defs.update(json.loads(s6.read_text(encoding="utf-8")))
        if local.exists():
            defs.update(json.loads(local.read_text(encoding="utf-8")))
        return defs
    return {}


def build_index(defs: dict[str, dict]) -> dict[str, list[tuple[str, str, dict]]]:
    """
    Build an index from first word -> list of (full_key, first_words, definition).
    first_words is the number of words in the key for greedy matching.
    """
    index: dict[str, list[tuple[str, str, dict]]] = {}
    for key, d in defs.items():
        first_word = key.split()[0] if key else ""
        if first_word not in index:
            index[first_word] = []
        index[first_word].append((key, d))
    # Sort each bucket by key length descending for greedy matching
    for first_word in index:
        index[first_word].sort(key=lambda x: len(x[0]), reverse=True)
    return index


def link_line(line: str, defs: dict[str, dict], index: dict, act: str) -> tuple[str, list[str]]:
    """
    Replace *term markers with hyperlinks.

    At each '*' we look up the first word after the star in the index,
    then try matching the longest definition from that bucket.
    """
    unresolved: list[str] = []
    result: list[str] = []
    i = 0

    while i < len(line):
        if line[i] != "*":
            result.append(line[i])
            i += 1
            continue

        remaining = line[i + 1:]
        # Extract first word after *
        word_match = re.match(r"^([A-Za-z][A-Za-z0-9'-]*)", remaining)
        if not word_match:
            result.append(line[i])
            i += 1
            continue

        first_word = word_match.group(1).lower()
        bucket = index.get(first_word, [])

        matched_term: str | None = None
        matched_def: dict | None = None

        for key, d in bucket:
            escaped = re.escape(key)
            pat = re.compile(r"^" + escaped + r"s?\b", re.IGNORECASE)
            m = pat.match(remaining)
            if m:
                matched_term = m.group(0)
                matched_def = d
                break

        if matched_term and matched_def:
            slug = matched_def["anchor"]
            section = matched_def["section"]
            link = f"[*{matched_term}*](/{act}/s{section}#{slug})"
            result.append(link)
            i += 1 + len(matched_term)
        else:
            candidate = remaining[:30].split()[0].lower() if remaining else ""
            if len(candidate) > 2:
                unresolved.append(candidate)
            result.append(line[i])
            i += 1

    return "".join(result), unresolved


def process_file(md_path: Path, defs: dict[str, dict], index: dict, act: str) -> list[str]:
    """Process one markdown file and return list of unresolved terms."""
    content = md_path.read_text(encoding="utf-8")

    if content.startswith("---"):
        fm_end = content.find("---", 3)
        frontmatter = content[: fm_end + 3]
        body = content[fm_end + 3:]
    else:
        frontmatter = ""
        body = content

    new_lines: list[str] = []
    all_unresolved: list[str] = []

    for line in body.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("<") and not stripped.startswith("<*"):
            new_lines.append(line)
            continue

        new_line, unresolved = link_line(line, defs, index, act)
        new_lines.append(new_line)
        all_unresolved.extend(unresolved)

    md_path.write_text(frontmatter + "".join(new_lines), encoding="utf-8")
    return all_unresolved


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--act", choices=["itaa-1997", "itaa-1936", "gst-1999"], required=True)
    ap.add_argument("--data-dir", type=Path, default=None)
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args()

    logging.basicConfig(level=args.log_level, format="%(message)s")

    base = Path.home() / "legislation-explorer"
    data_dir = args.data_dir or base / "data" / args.act
    sections_dir = data_dir / "sections"

    defs = load_definitions(data_dir, args.act)
    if not defs:
        logging.error("No definitions found for %s", args.act)
        return

    index = build_index(defs)
    logging.info("Loaded %d definitions for %s", len(defs), args.act)

    md_files = sorted(sections_dir.rglob("*.md"))
    total_unresolved: set[str] = set()
    total_linked = 0

    for md_path in md_files:
        if md_path.name == "995-1.md" and args.act == "itaa-1997":
            continue
        if md_path.name == "195-1.md" and args.act == "gst-1999":
            continue

        unresolved = process_file(md_path, defs, index, args.act)
        total_unresolved.update(unresolved)

    for md_path in md_files:
        content = md_path.read_text(encoding="utf-8")
        total_linked += content.count(f"](/{args.act}/s")

    log_path = data_dir / "unresolved-terms.log"
    log_path.write_text("\n".join(sorted(total_unresolved)), encoding="utf-8")

    logging.info("Processed %d files", len(md_files))
    logging.info("Linked terms: %d", total_linked)
    logging.info("Unresolved unique terms: %d (logged to %s)", len(total_unresolved), log_path)


if __name__ == "__main__":
    main()
