#!/usr/bin/env python3
"""
Fix remaining data quality issues in legislation-explorer data/.

1. Remove form feed characters and running headers from all .md files
2. Remove compilation metadata lines from TAA 1953 and GST 1999
3. Fix GST 195-1.md (truncate at endnotes / Schedule content)
4. Fix Master Tax Examples broken paragraph titles
"""

import re
from pathlib import Path

BASE = Path("/home/harrison/legislation-explorer/data")

# ============================================================================
# FIX 1: Form feeds and running headers
# ============================================================================

def clean_form_feeds_and_headers():
    """Remove form feed chars and concatenated running headers from all acts."""
    acts = ["itaa-1936", "gst-1999", "taa-1953"]
    total = 0
    for act in acts:
        section_dir = BASE / act / "sections"
        if not section_dir.exists():
            continue
        for md_file in section_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            original = content
            # Remove form feed characters
            content = content.replace("\f", "")
            # Remove lines that are just running headers (title + structural element)
            lines = content.split("\n")
            cleaned = []
            for line in lines:
                stripped = line.strip()
                # Skip standalone running headers
                if re.match(r"^(Schedule \d+.*|Collection and recovery of income tax and other liabilities Schedule \d+|The basic rules Chapter \d+|The special rules Chapter \d+|Miscellaneous Chapter \d+|Interpretative provisions Chapter \d+|Administration, collection and recovery Chapter \d+)$", stripped):
                    continue
                cleaned.append(line)
            content = "\n".join(cleaned)
            # Collapse multiple blank lines
            content = re.sub(r"\n{3,}", "\n\n", content)
            if content != original:
                md_file.write_text(content, encoding="utf-8")
                total += 1
    print(f"Cleaned form feeds/headers in {total} files")


# ============================================================================
# FIX 2: Compilation metadata lines
# ============================================================================

def clean_compilation_metadata():
    """Remove compilation metadata lines from TAA 1953 and GST 1999."""
    acts = ["taa-1953", "gst-1999"]
    total = 0
    for act in acts:
        section_dir = BASE / act / "sections"
        if not section_dir.exists():
            continue
        for md_file in section_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            original = content
            lines = content.split("\n")
            cleaned = []
            for line in lines:
                stripped = line.strip()
                if re.match(r"^Compilation No\.\s*\d+\s*Compilation date:\s*\d{2}/\d{2}/\d{4}$", stripped):
                    continue
                if re.match(r"^Authorised Version\s+C\d+.*$", stripped):
                    continue
                if re.match(r"^Registered:\s*\d{2}/\d{2}/\d{4}$", stripped):
                    continue
                cleaned.append(line)
            content = "\n".join(cleaned)
            # Collapse multiple blank lines
            content = re.sub(r"\n{3,}", "\n\n", content)
            if content != original:
                md_file.write_text(content, encoding="utf-8")
                total += 1
    print(f"Cleaned compilation metadata in {total} files")


# ============================================================================
# FIX 3: GST 195-1.md endnote leakage
# ============================================================================

def fix_gst_1951():
    """Truncate GST 195-1.md at the start of endnotes/schedule leakage."""
    path = BASE / "gst-1999/sections/part-6-3/division-195/195-1.md"
    if not path.exists():
        print("GST 195-1.md not found, skipping")
        return
    content = path.read_text(encoding="utf-8")
    original = content
    # Find the first occurrence of endnote or schedule leakage patterns
    markers = [
        "Endnotes",
        "Schedule 2",
        "Schedule 3",
        "Medical aids and appliances",
        "About the endnotes",
        "Abbreviation key",
        "Legislation history",
        "Amendment history",
    ]
    cut_pos = len(content)
    for marker in markers:
        pos = content.find(marker)
        if pos != -1 and pos < cut_pos:
            # Make sure it's a real structural marker, not inline text
            # Check if it's at the start of a line
            line_start = content.rfind("\n", 0, pos)
            if line_start == -1:
                line_start = 0
            else:
                line_start += 1
            if pos - line_start < 5:  # near start of line
                cut_pos = pos

    if cut_pos < len(content):
        content = content[:cut_pos].rstrip() + "\n"
        # Also remove any trailing blockquote markers that got cut
        content = re.sub(r"\n>\s*\n", "\n", content)
        content = re.sub(r"\n{3,}", "\n\n", content)
        if content != original:
            path.write_text(content, encoding="utf-8")
            print(f"Truncated GST 195-1.md at position {cut_pos} (removed {len(original) - len(content)} chars)")
        else:
            print("GST 195-1.md: no change after truncation")
    else:
        print("GST 195-1.md: no endnote marker found")


# ============================================================================
# FIX 4: Master Tax Examples broken paragraph titles
# ============================================================================

def fix_mte_broken_titles():
    """Fix broken 'Worked example:' titles that span multiple lines in MTE."""
    mte_dir = BASE / "master-tax-examples" / "sections"
    if not mte_dir.exists():
        return
    total = 0
    for md_file in mte_dir.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        original = content
        lines = content.split("\n")
        cleaned = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            # Detect "Worked example: ..." followed by continuation on next line(s)
            if re.match(r"^Worked example:\s*\S", stripped) and not stripped.endswith("."):
                # Gather continuation lines
                merged = stripped
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if not next_line:
                        break
                    # Stop if next line is a structural element
                    if next_line.startswith("##") or next_line.startswith("#") or next_line.startswith("*Refs:"):
                        break
                    # Stop if next line starts with bullet
                    if next_line.startswith("-") or next_line.startswith("•"):
                        break
                    merged += " " + next_line
                    j += 1
                cleaned.append(merged)
                i = j
                continue
            cleaned.append(line)
            i += 1
        content = "\n".join(cleaned)
        if content != original:
            md_file.write_text(content, encoding="utf-8")
            total += 1
    print(f"Fixed broken titles in {total} MTE files")


if __name__ == "__main__":
    print("=" * 60)
    print("FIX 1: Form feeds and running headers")
    print("=" * 60)
    clean_form_feeds_and_headers()

    print()
    print("=" * 60)
    print("FIX 2: Compilation metadata lines")
    print("=" * 60)
    clean_compilation_metadata()

    print()
    print("=" * 60)
    print("FIX 3: GST 195-1 endnote leakage")
    print("=" * 60)
    fix_gst_1951()

    print()
    print("=" * 60)
    print("FIX 4: MTE broken paragraph titles")
    print("=" * 60)
    fix_mte_broken_titles()

    print()
    print("=" * 60)
    print("Done.")
    print("=" * 60)
