#!/usr/bin/env python3
"""
Audit all legislation sections for broken definition links.
Checks both raw .md files and API-processed output for:
1. Nested links: [[*term*](url)](other) or [*text [*term*](url)]
2. Incomplete links: [*term(] without closing )
3. Regex-overrun: links that span punctuation like ' or ;
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from collections import Counter

BASE = Path("/home/harrison/legislation-explorer/data")

# Patterns that indicate broken links
BROKEN_PATTERNS = {
    "nested_link": re.compile(r"\[\[[^\]]+\]\([^)]+\)"),  # [[...](...)
    "nested_def_in_link": re.compile(r"\[[^\]]*\[\*[^\]]+\]\([^)]+\)"),  # [..[*term*](url)
    "incomplete_link": re.compile(r"\[\*[^\]]+\]\([^)]*$"),  # [*term](url  (no closing ))
    "double_star_in_link": re.compile(r"\[\*\*"),  # [** — bold inside link
    "unclosed_link": re.compile(r"\[\*[^\]]+\]\([^)]*\["),  # [*text](...[ — unclosed
}

# Patterns in RAW markdown that predict broken output
RAW_RISK_PATTERNS = {
    "star_before_apostrophe": re.compile(r"\*\w+'\w"),  # *asset's — regex will overrun
    "star_before_semicolon": re.compile(r"\*\w+;"),  # *term; — regex won't stop
    "star_before_colon": re.compile(r"\*\w+:"),  # *term: — regex won't stop
    "star_before_comma": re.compile(r"\*\w+,"),  # *term, — regex won't stop
    "star_before_period": re.compile(r"\*\w+\."),  # *term. — regex won't stop
    "consecutive_stars": re.compile(r"\*\w+\s+\*\w"),  # *term1 *term2 — may merge
}

def audit_raw_file(md_path: Path) -> list[dict]:
    content = md_path.read_text(encoding="utf-8")
    issues = []
    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        # Skip frontmatter
        if i <= 15 and line.startswith("---"):
            continue
        for name, pat in RAW_RISK_PATTERNS.items():
            for m in pat.finditer(line):
                issues.append({
                    "line": i,
                    "pattern": name,
                    "match": m.group(0),
                    "context": line[max(0, m.start()-20):m.end()+20],
                })
    return issues

def audit_processed_output(body: str) -> list[dict]:
    issues = []
    lines = body.split("\n")
    for i, line in enumerate(lines, 1):
        for name, pat in BROKEN_PATTERNS.items():
            for m in pat.finditer(line):
                issues.append({
                    "line": i,
                    "pattern": name,
                    "match": m.group(0)[:80],
                    "context": line[max(0, m.start()-30):m.end()+30],
                })
    return issues

def main():
    total_sections = 0
    raw_risk_sections = 0
    processed_broken_sections = 0
    
    raw_risk_summary = Counter()
    broken_summary = Counter()
    
    examples_raw = []
    examples_processed = []
    
    for act_dir in [BASE / "itaa-1997", BASE / "itaa-1936", BASE / "gst-1999", BASE / "taa-1953"]:
        tree_path = act_dir / "tree.json"
        if not tree_path.exists():
            continue
        tree = json.loads(tree_path.read_text())
        
        def walk(node, act_name, path_prefix=""):
            nonlocal total_sections, raw_risk_sections, processed_broken_sections
            if isinstance(node, dict):
                node_type = node.get("type", "")
                if node_type == "section" or (node.get("id") and "path" in node):
                    total_sections += 1
                    sec_id = node["id"]
                    rel_path = node.get("path", f"{path_prefix}/{sec_id}.md")
                    md_path = act_dir / "sections" / rel_path
                    
                    if md_path.exists():
                        # Audit raw file
                        raw_issues = audit_raw_file(md_path)
                        if raw_issues:
                            raw_risk_sections += 1
                            for iss in raw_issues:
                                raw_risk_summary[iss["pattern"]] += 1
                            if len(examples_raw) < 10:
                                examples_raw.append({
                                    "act": act_name,
                                    "section": sec_id,
                                    "issues": raw_issues[:3],
                                })
                        
                        # Audit processed output (simulate what backend does)
                        content = md_path.read_text(encoding="utf-8")
                        if content.startswith("---"):
                            fm_end = content.find("---", 3)
                            if fm_end != -1:
                                body = content[fm_end+3:]
                            else:
                                body = content
                        else:
                            body = content
                        
                        proc_issues = audit_processed_output(body)
                        if proc_issues:
                            processed_broken_sections += 1
                            for iss in proc_issues:
                                broken_summary[iss["pattern"]] += 1
                            if len(examples_processed) < 10:
                                examples_processed.append({
                                    "act": act_name,
                                    "section": sec_id,
                                    "issues": proc_issues[:3],
                                })
                
                # Recurse into children or parts/divisions/sections
                for key in ["children", "parts", "divisions", "sections", "subdivisions"]:
                    for child in node.get(key, []):
                        walk(child, act_name)
        
        # Tree root may have parts[] instead of children[]
        root = tree
        if "parts" in root:
            for part in root["parts"]:
                walk(part, act_dir.name)
        else:
            walk(root, act_dir.name)
    
    print("=" * 60)
    print("BROKEN LINK AUDIT RESULTS")
    print("=" * 60)
    print(f"\nTotal sections scanned: {total_sections}")
    print(f"Sections with raw-risk patterns (predict broken links): {raw_risk_sections}")
    print(f"Sections with already-broken processed links: {processed_broken_sections}")
    
    print("\n--- RAW RISK PATTERNS (predict future breakage) ---")
    for pat, count in raw_risk_summary.most_common():
        print(f"  {pat}: {count} occurrences")
    
    print("\n--- ALREADY BROKEN IN PROCESSED OUTPUT ---")
    for pat, count in broken_summary.most_common():
        print(f"  {pat}: {count} occurrences")
    
    print("\n--- EXAMPLES: Raw risk ---")
    for ex in examples_raw:
        print(f"\n{ex['act']} s{ex['section']}:")
        for iss in ex["issues"]:
            print(f"  Line {iss['line']} [{iss['pattern']}]: {iss['context'][:100]}")
    
    print("\n--- EXAMPLES: Already broken ---")
    for ex in examples_processed:
        print(f"\n{ex['act']} s{ex['section']}:")
        for iss in ex["issues"]:
            print(f"  Line {iss['line']} [{iss['pattern']}]: {iss['context'][:100]}")

if __name__ == "__main__":
    main()
