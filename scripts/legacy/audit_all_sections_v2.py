#!/usr/bin/env python3
"""
Better section quality audit.
Distinguishes truly empty from short but legitimate.
"""
import os, re, sys, json

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else "/home/harrison/legislation-explorer/data"

def audit_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    issues = []

    # Split frontmatter and body
    if not content.startswith('---'):
        return [('missing_frontmatter', 'No YAML frontmatter')]

    parts = content.split('---', 2)
    if len(parts) < 3:
        return [('malformed_frontmatter', 'Could not parse')]

    body = parts[2]

    # Parse frontmatter
    fm = {}
    for line in parts[1].strip().split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")

    title = fm.get('section_title', '')
    section_id = fm.get('section', '')

    # === CRITERIA 1: Truly empty (no text between heading and footer) ===
    # Strip heading, horizontal rules, footer, blank lines
    body_lines = body.split('\n')
    # Remove the markdown heading line
    content_lines = []
    for line in body_lines:
        stripped = line.strip()
        if stripped.startswith('# '):  # Skip the title heading
            continue
        if stripped == '---':  # Skip HR
            continue
        if stripped.startswith('*Last updated'):  # Skip footer
            continue
        if stripped == '':  # Skip blank lines for counting
            continue
        content_lines.append(stripped)

    # Truly empty = zero content lines
    if len(content_lines) == 0:
        issues.append(('truly_empty', 'Zero content lines'))

    # === CRITERIA 2: Garbled title ===
    if '_____________________________________' in title:
        issues.append(('garbled_title_underscores', title[:80]))
    if re.search(r'^\d+\.', title) and len(title) > 60:
        issues.append(('garbled_title_numbered_list', title[:80]))

    # === CRITERIA 3: PDF artifacts in body ===
    if 'Authorised Version' in body:
        issues.append(('pdf_authorised_footer', 'Authorised Version found in body'))
    if '_____________________________________' in body:
        issues.append(('pdf_underscore_separator', 'Underscore separator found in body'))
    # Compilation No. ONLY if not part of our standard footer
    if 'Compilation No.' in body and '*Last updated' not in body:
        issues.append(('pdf_compilation_footer', 'Compilation No. found in body'))

    # === CRITERIA 4: Broken markdown links ===
    nested = re.findall(r'\[\*[^\]]+\[\*', body)
    if nested:
        issues.append(('broken_link_nested', nested[0][:60]))
    greedy = re.findall(r'\[\*[^\]]+[.;:,!?]\*\]\([^)]+\)', body)
    if greedy:
        issues.append(('broken_link_greedy', greedy[0][:60]))
    double = re.findall(r'\[\[[^\]]+\]\([^)]+\)\]', body)
    if double:
        issues.append(('broken_link_double', double[0][:60]))

    # === CRITERIA 5: Page number artifacts ===
    page_nums = re.findall(r'^\s*\d+\s+Income Tax Assessment Act', body, re.MULTILINE)
    if page_nums:
        issues.append(('pdf_page_number', page_nums[0][:60]))

    return issues


def main():
    results = []
    total = 0

    for act_dir in sorted(os.listdir(DATA_DIR)):
        act_path = os.path.join(DATA_DIR, act_dir)
        if not os.path.isdir(act_path):
            continue

        sections_dir = os.path.join(act_path, 'sections')
        if not os.path.exists(sections_dir):
            continue

        for root, dirs, files in os.walk(sections_dir):
            for fname in sorted(files):
                if not fname.endswith('.md'):
                    continue
                total += 1
                path = os.path.join(root, fname)
                rel = os.path.relpath(path, DATA_DIR)
                issues = audit_file(path)
                if issues:
                    results.append({
                        'file': rel,
                        'section': fname.replace('.md', ''),
                        'issues': issues
                    })

    print(f"Audited {total} section files")
    print(f"Files with issues: {len(results)}")
    print()

    by_type = {}
    for r in results:
        for issue_type, detail in r['issues']:
            by_type.setdefault(issue_type, []).append({
                'file': r['file'],
                'section': r['section'],
                'detail': detail
            })

    for issue_type, items in sorted(by_type.items(), key=lambda x: -len(x[1])):
        print(f"\n{issue_type}: {len(items)} files")
        for item in items[:5]:
            print(f"  {item['file']} -> {item['detail'][:70]}")
        if len(items) > 5:
            print(f"  ... and {len(items)-5} more")

    out_path = '/home/harrison/legislation-explorer/audit_results_v2.json'
    with open(out_path, 'w') as f:
        json.dump({
            'total_audited': total,
            'files_with_issues': len(results),
            'by_type': {k: len(v) for k, v in by_type.items()},
            'details': results
        }, f, indent=2)
    print(f"\nFull results: {out_path}")


if __name__ == '__main__':
    main()
