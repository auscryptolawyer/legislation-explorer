#!/usr/bin/env python3
"""
Comprehensive section quality audit.
Flags:
- Empty or near-empty bodies (only header/footer, no substantive text)
- Garbled titles containing body text, underscores, or numbered lists
- PDF artifacts remaining in body (Compilation No., Authorised Version, page numbers)
- Broken markdown links
"""
import os, re, sys, json, glob

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else "/home/harrison/legislation-explorer/data"

def audit_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    issues = []

    # Split frontmatter and body
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            body = parts[2]
        else:
            return [('malformed_frontmatter', 'Could not parse frontmatter')]
    else:
        return [('missing_frontmatter', 'No YAML frontmatter')]

    # Parse frontmatter
    fm = {}
    for line in frontmatter.strip().split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")

    title = fm.get('section_title', '')
    section_id = fm.get('section', '')

    # Check 1: Garbled title
    if '_____________________________________' in title:
        issues.append(('garbled_title_underscores', title[:80]))
    if re.search(r'\d+\.', title) and len(title) > 60:
        issues.append(('garbled_title_numbered_list', title[:80]))
    if len(title) > 100:
        issues.append(('suspiciously_long_title', title[:80]))

    # Check 2: Body too short (just header + footer)
    body_lines = [l for l in body.split('\n') if l.strip()]
    non_footer_lines = [l for l in body_lines if not l.startswith('*Last updated') and l.strip() != '---']
    if len(non_footer_lines) <= 2:
        issues.append(('near_empty_body', f'{len(non_footer_lines)} substantive lines'))

    # Check 3: PDF artifacts in body
    if 'Compilation No.' in body and 'Last updated' in body:
        # This is fine - it's the footer we add
        pass
    elif 'Compilation No.' in body:
        issues.append(('pdf_compilation_footer', 'Compilation No. found in body'))

    if 'Authorised Version' in body:
        issues.append(('pdf_authorised_footer', 'Authorised Version found in body'))

    if '_____________________________________' in body:
        issues.append(('pdf_underscore_separator', 'Underscore separator found in body'))

    # Check 4: Broken markdown links
    # Nested brackets: [*term [*other*](...)]
    nested = re.findall(r'\[\*[^\]]+\[\*', body)
    if nested:
        issues.append(('broken_link_nested', nested[0][:60]))

    # Greedy period in link: [*term.](/...)
    greedy = re.findall(r'\[\*[^\]]+[.;:,!?]\*\]\([^)]+\)', body)
    if greedy:
        issues.append(('broken_link_greedy', greedy[0][:60]))

    # Double bracket: [[*term*](/...)]
    double = re.findall(r'\[\[[^\]]+\]\([^)]+\)\]', body)
    if double:
        issues.append(('broken_link_double', double[0][:60]))

    # Check 5: Page number artifacts (standalone numbers at start of line in body)
    page_nums = re.findall(r'^\s*\d+\s+Income Tax Assessment Act', body, re.MULTILINE)
    if page_nums:
        issues.append(('pdf_page_number', page_nums[0][:60]))

    return issues


def main():
    results = []
    total = 0

    for act_dir in os.listdir(DATA_DIR):
        act_path = os.path.join(DATA_DIR, act_dir)
        if not os.path.isdir(act_path):
            continue

        sections_dir = os.path.join(act_path, 'sections')
        if not os.path.exists(sections_dir):
            continue

        for root, dirs, files in os.walk(sections_dir):
            for fname in files:
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

    # Summary
    print(f"Audited {total} section files")
    print(f"Files with issues: {len(results)}")
    print()

    # Group by issue type
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
            print(f"  {item['file']} -> {item['detail'][:60]}")
        if len(items) > 5:
            print(f"  ... and {len(items)-5} more")

    # Write full results
    out_path = '/home/harrison/legislation-explorer/audit_results.json'
    with open(out_path, 'w') as f:
        json.dump({
            'total_audited': total,
            'files_with_issues': len(results),
            'by_type': {k: len(v) for k, v in by_type.items()},
            'details': results
        }, f, indent=2)
    print(f"\nFull results written to {out_path}")


if __name__ == '__main__':
    main()
