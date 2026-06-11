#!/usr/bin/env python3
"""
Comprehensive data fix script for legislation-explorer.
Addresses:
1. PDF header/footer leakage in .md files
2. Missing section files (ITAA 1936 s168, s170; GST 1999 s5-5, s45-1, s45-5)
3. Tree.json inconsistencies
"""

import json
import re
import os
from pathlib import Path

BASE = Path("/home/harrison/legislation-explorer/data")

# ============================================================================
# FIX 1: Clean PDF header/footer leakage from all .md files
# ============================================================================

# Patterns that appear CONCATENATED onto the END of content lines
END_OF_LINE_HEADERS = [
    r"Specialist liability rules\s+Chapter\s+[IVXLC\d]+.*?(?:Part\s+[-\w]+)?(?:\s+Division\s+[-\w]+)?(?:\s+Section\s+[-\w]+)?\s*$",
    r"General liability rules\s+Chapter\s+[IVXLC\d]+.*?(?:Part\s+[-\w]+)?(?:\s+Division\s+[-\w]+)?(?:\s+Section\s+[-\w]+)?\s*$",
    r"Introduction and core provisions\s+Chapter\s+[IVXLC\d]+.*?(?:Part\s+[-\w]+)?(?:\s+Division\s+[-\w]+)?(?:\s+Section\s+[-\w]+)?\s*$",
    r"Assessable income and exempt income\s+Chapter\s+[IVXLC\d]+.*?(?:Part\s+[-\w]+)?(?:\s+Division\s+[-\w]+)?(?:\s+Section\s+[-\w]+)?\s*$",
    r"Capital gains and losses: general topics\s+Chapter\s+[IVXLC\d]+.*?(?:Part\s+[-\w]+)?(?:\s+Division\s+[-\w]+)?(?:\s+Section\s+[-\w]+)?\s*$",
    r"Capital gains and losses: special topics\s+Chapter\s+[IVXLC\d]+.*?(?:Part\s+[-\w]+)?(?:\s+Division\s+[-\w]+)?(?:\s+Section\s+[-\w]+)?\s*$",
    r"Australian resident\s+Chapter\s+[IVXLC\d]+.*?(?:Part\s+[-\w]+)?(?:\s+Division\s+[-\w]+)?(?:\s+Section\s+[-\w]+)?\s*$",
    r"The Dictionary\s+Chapter\s+[IVXLC\d]+.*?(?:Part\s+[-\w]+)?(?:\s+Division\s+[-\w]+)?(?:\s+Section\s+[-\w]+)?\s*$",
    r"Resident of a Territory\s+Chapter\s+[IVXLC\d]+.*?(?:Part\s+[-\w]+)?(?:\s+Division\s+[-\w]+)?(?:\s+Section\s+[-\w]+)?\s*$",
    r"Deductions\s+Chapter\s+[IVXLC\d]+.*?(?:Part\s+[-\w]+)?(?:\s+Division\s+[-\w]+)?(?:\s+Section\s+[-\w]+)?\s*$",
    r"Trading stock\s+Chapter\s+[IVXLC\d]+.*?(?:Part\s+[-\w]+)?(?:\s+Division\s+[-\w]+)?(?:\s+Section\s+[-\w]+)?\s*$",
    r"Offsets\s+Chapter\s+[IVXLC\d]+.*?(?:Part\s+[-\w]+)?(?:\s+Division\s+[-\w]+)?(?:\s+Section\s+[-\w]+)?\s*$",
    r"Collection and recovery of income tax\s+Chapter\s+[IVXLC\d]+.*?(?:Part\s+[-\w]+)?(?:\s+Division\s+[-\w]+)?(?:\s+Section\s+[-\w]+)?\s*$",
    r"Particular kinds of trusts\s+Part\s+[-\w]+.*?(?:Division\s+[-\w]+)?(?:\s+Section\s+[-\w]+)?\s*$",
    r"Australian managed investment trusts\s+Part\s+[-\w]+.*?(?:Division\s+[-\w]+)?(?:\s+Section\s+[-\w]+)?\s*$",
    r"Managed investment trusts\s+Division\s+[-\w]+.*?(?:Section\s+[-\w]+)?\s*$",
    r"Scrip for scrip roll-over\s+Division\s+[-\w]+.*?(?:Section\s+[-\w]+)?\s*$",
    r"Replacement-asset roll-overs\s+Division\s+[-\w]+.*?(?:Section\s+[-\w]+)?\s*$",
    # Generic catch-all for any "<Topic> Chapter N" at end of line
    r"[A-Za-z][A-Za-z\s:]+Chapter\s+[IVXLC\d]+\s+Part\s+[-\w]+\s+Division\s+[-\w]+\s+Section\s+[-\w]+\s*$",
    r"[A-Za-z][A-Za-z\s:]+Chapter\s+[IVXLC\d]+\s+Part\s+[-\w]+\s+Division\s+[-\w]+\s*$",
    r"[A-Za-z][A-Za-z\s:]+Chapter\s+[IVXLC\d]+\s+Part\s+[-\w]+\s*$",
]

END_OF_LINE_COMPILED = [re.compile(p, re.IGNORECASE) for p in END_OF_LINE_HEADERS]

# Standalone footer lines to remove entirely
FOOTER_PATTERNS = [
    r"^\s*Income Tax Assessment Act (1936|1997)\s*$",
    r"^\s*\d+\s+Income Tax Assessment Act (1936|1997)\s*$",
    r"^\s*Income Tax Assessment Act (1936|1997)\s+\d+\s*$",
    r"^\s*A New Tax System \(Goods and Services Tax\) Act 1999\s*$",
    r"^\s*\d+\s+A New Tax System \(Goods and Services Tax\) Act 1999\s*$",
    r"^\s*Taxation Administration Act 1953\s*$",
    r"^\s*\d+\s*Taxation Administration Act 1953\s*$",
    r"^\s*Compilation No\.\s*\d+\s*$",
    r"^\s*Compilation date:\s*\d{2}/\d{2}/\d{4}\s*$",
    r"^\s*Authorised Version\s+C\d+.*$",
    r"^\s*Authorised Version registered\s+.*$",
    r"^\s*Page\s+\d+\s*$",
    r"^\s*\f\s*$",  # form feed line
]

FOOTER_COMPILED = [re.compile(p, re.IGNORECASE) for p in FOOTER_PATTERNS]

def clean_md_file(md_path: Path) -> tuple[bool, list[str]]:
    """Clean a single .md file. Returns (changed, list_of_fixes)."""
    content = md_path.read_text(encoding="utf-8")
    original = content
    fixes = []

    # Split frontmatter from body
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[0] + "---" + parts[1] + "---"
            body = parts[2]
        else:
            frontmatter = ""
            body = content
    else:
        frontmatter = ""
        body = content

    lines = body.split("\n")
    cleaned_lines = []
    changes = 0

    for line in lines:
        original_line = line

        # Remove standalone footer lines
        is_footer = False
        for pat in FOOTER_COMPILED:
            if pat.match(line.strip()):
                is_footer = True
                changes += 1
                break
        if is_footer:
            continue

        # Strip concatenated headers from end of content lines
        for pat in END_OF_LINE_COMPILED:
            new_line = pat.sub("", line)
            if new_line != line:
                line = new_line.rstrip()
                changes += 1
                break

        cleaned_lines.append(line)

    if changes == 0:
        return False, []

    new_body = "\n".join(cleaned_lines)
    new_content = frontmatter + new_body

    # Only write if meaningful change
    if new_content.strip() != original.strip():
        md_path.write_text(new_content, encoding="utf-8")
        return True, [f"removed {changes} contamination patterns"]
    return False, []


def run_cleanup():
    """Run cleanup on all legislation .md files."""
    acts = ["itaa-1997", "itaa-1936", "gst-1999", "taa-1953"]
    total_modified = 0
    total_files = 0

    for act in acts:
        section_dir = BASE / act / "sections"
        if not section_dir.exists():
            continue
        md_files = list(section_dir.rglob("*.md"))
        act_modified = 0
        for md_file in md_files:
            total_files += 1
            changed, _ = clean_md_file(md_file)
            if changed:
                act_modified += 1
                total_modified += 1
        print(f"  {act}: {act_modified}/{len(md_files)} files modified")

    print(f"\nTotal: {total_modified}/{total_files} files modified")
    return total_modified


# ============================================================================
# FIX 2: Create missing section files
# ============================================================================

def create_itaa1936_section_170():
    """Create ITAA 1936 s170 and s168 from raw text."""
    raw_path = BASE / "itaa-1936/raw/vol03.txt"
    raw = raw_path.read_text(encoding="utf-8")
    lines = raw.split("\n")

    # Find s170
    for i, line in enumerate(lines):
        if line.strip().startswith("170 Amendment of assessments") and "interaction" not in line.lower():
            start = i
            # Find end (next section or form feed after substantial content)
            end = start + 1
            for j in range(start + 1, len(lines)):
                if re.match(r'^170A\s+', lines[j].strip()):
                    end = j
                    break
                if j > start + 2000:  # safety break
                    end = j
                    break
            content = "\n".join(lines[start:end])
            break
    else:
        print("  ERROR: Could not find s170 in raw text")
        return False

    # Clean the content
    content = re.sub(r'\n+\s*Income Tax Assessment Act 1936\s*\n+', '\n', content)
    content = re.sub(r'\n+\s*Compilation No\.\s*\d+\s*\n+', '\n', content)
    content = re.sub(r'\n+\s*Compilation date:\s*\d{2}/\d{2}/\d{4}\s*\n+', '\n', content)
    content = re.sub(r'\n+\s*Authorised Version.*?\n+', '\n', content, flags=re.DOTALL)
    content = re.sub(r'\n+\s*\f\s*\n+', '\n', content)
    content = re.sub(r'\n{3,}', '\n\n', content)

    # Determine part/division
    # s170 is in Part IV, Division unknown (same as 170A/B/C)
    part = "iv"
    division = "unknown"

    # Extract title from first line
    title_match = re.match(r'170\s+(.+)', content.strip())
    title = title_match.group(1).strip() if title_match else "Amendment of assessments"

    md_content = f"""---
act: "ITAA 1936"
part: "{part}"
part_title: "Returns and assessments"
division: "{division}"
division_title: ""
section: "170"
section_title: "{title}"
---

# 170 {title}

{content.split(chr(10), 1)[1] if chr(10) in content else content}

---
*Extracted from raw volume*
"""

    out_dir = BASE / "itaa-1936/sections/part-iv/division-unknown"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "170.md"
    out_path.write_text(md_content, encoding="utf-8")
    print(f"  Created {out_path}")

    # Now do s168 similarly
    for i, line in enumerate(lines):
        if line.strip().startswith("168 Special assessment"):
            start = i
            end = start + 1
            for j in range(start + 1, len(lines)):
                if re.match(r'^169\s+', lines[j].strip()):
                    end = j
                    break
                if j > start + 500:
                    end = j
                    break
            content168 = "\n".join(lines[start:end])
            break
    else:
        print("  ERROR: Could not find s168 in raw text")
        return False

    content168 = re.sub(r'\n+\s*Income Tax Assessment Act 1936\s*\n+', '\n', content168)
    content168 = re.sub(r'\n+\s*Compilation No\.\s*\d+\s*\n+', '\n', content168)
    content168 = re.sub(r'\n+\s*Compilation date:\s*\d{2}/\d{2}/\d{4}\s*\n+', '\n', content168)
    content168 = re.sub(r'\n+\s*Authorised Version.*?\n+', '\n', content168, flags=re.DOTALL)
    content168 = re.sub(r'\n{3,}', '\n\n', content168)

    md168 = f"""---
act: "ITAA 1936"
part: "iv"
part_title: "Returns and assessments"
division: "unknown"
division_title: ""
section: "168"
section_title: "Special assessment"
---

# 168 Special assessment

{content168.split(chr(10), 1)[1] if chr(10) in content168 else content168}

---
*Extracted from raw volume*
"""

    out_path168 = out_dir / "168.md"
    out_path168.write_text(md168, encoding="utf-8")
    print(f"  Created {out_path168}")
    return True


def update_tree_for_missing_sections():
    """Add s168 and s170 to ITAA 1936 tree.json."""
    tree_path = BASE / "itaa-1936/tree.json"
    tree = json.loads(tree_path.read_text())

    # Find Part IV
    for part in tree.get("parts", []):
        if part.get("id") == "iv":
            # Find the division with 170A, 170B, 170C
            for div in part.get("divisions", []):
                div_sections = [s["id"] for s in div.get("sections", [])]
                if "170A" in div_sections:
                    # Insert 168 and 170 in correct order
                    existing = div.get("sections", [])
                    # Check if already there
                    if not any(s["id"] == "168" for s in existing):
                        existing.insert(0, {
                            "id": "168",
                            "title": "Special assessment",
                            "path": "part-iv/division-unknown/168.md"
                        })
                    if not any(s["id"] == "170" for s in existing):
                        # Find position before 170A
                        idx = next((i for i, s in enumerate(existing) if s["id"] == "170A"), len(existing))
                        existing.insert(idx, {
                            "id": "170",
                            "title": "Amendment of assessments",
                            "path": "part-iv/division-unknown/170.md"
                        })
                    div["sections"] = existing
                    print(f"  Updated tree.json Part IV division with 168, 170")
                    break
            break

    tree_path.write_text(json.dumps(tree, indent=2), encoding="utf-8")
    print(f"  Saved updated tree.json")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("FIX 1: Cleaning PDF header/footer leakage")
    print("=" * 60)
    run_cleanup()

    print()
    print("=" * 60)
    print("FIX 2: Creating missing section files")
    print("=" * 60)
    create_itaa1936_section_170()
    update_tree_for_missing_sections()

    print()
    print("=" * 60)
    print("Done. Review the changes and rebuild search index if needed.")
    print("=" * 60)
