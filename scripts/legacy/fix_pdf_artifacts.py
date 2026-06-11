#!/usr/bin/env python3
import os, re, json

with open('audit_results_v2.json') as f:
    audit = json.load(f)

# Collect files needing cleanup
files_to_fix = set()
for item in audit['details']:
    for issue_type, _ in item['issues']:
        if issue_type in ('pdf_authorised_footer', 'pdf_underscore_separator', 'pdf_compilation_footer', 'pdf_page_number'):
            files_to_fix.add(item['file'])

print(f"Files to clean: {len(files_to_fix)}")

fixed_count = 0
for rel_path in sorted(files_to_fix):
    path = os.path.join('/home/harrison/legislation-explorer/data', rel_path)
    if not os.path.exists(path):
        continue

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # Split frontmatter and body
    if not content.startswith('---'):
        continue
    parts = content.split('---', 2)
    if len(parts) < 3:
        continue

    fm = parts[1]
    body = parts[2]

    # Remove underscore separator lines
    body = re.sub(r'_{20,}\s*\n?', '\n', body)

    # Remove Authorised Version lines
    body = re.sub(r'\s*Authorised Version\s+C\d+C\d+\s+registered\s+\d{2}/\d{2}/\d{4}\s*\n?', '\n', body)

    # Remove Compilation No. / Compilation date lines (not our footer)
    body = re.sub(r'\s*Compilation No\.\s*\d+\s+Compilation date:\s*\d{2}/\d{2}/\d{4}\s*\n?', '\n', body)

    # Remove page number + Act name lines
    body = re.sub(r'^\s*\d+\s+Income Tax Assessment Act\s+\d+\s*\n?', '\n', body, flags=re.MULTILINE)
    body = re.sub(r'^\s*\d+\s+Taxation Administration Act\s+\d+\s*\n?', '\n', body, flags=re.MULTILINE)
    body = re.sub(r'^\s*\d+\s+A New Tax System \(Goods and Services Tax\) Act\s+\d+\s*\n?', '\n', body, flags=re.MULTILINE)

    # Clean up excessive blank lines
    body = re.sub(r'\n{4,}', '\n\n\n', body)

    if body != parts[2]:
        new_content = '---' + fm + '---' + body
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        fixed_count += 1

print(f"Fixed {fixed_count} files")
