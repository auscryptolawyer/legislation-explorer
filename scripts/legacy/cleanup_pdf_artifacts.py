
import re
import os

def cleanup_md_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Patterns to remove
    patterns = [
        re.compile(r'^\s*Taxation Administration Act 1953\s*$', re.MULTILINE),
        re.compile(r'^\s*Compilation No\. \d+\s*$', re.MULTILINE),
        re.compile(r'^\s*Compilation date: \d{2}/\d{2}/\d{4}\s*$', re.MULTILINE),
        re.compile(r'^\s*Authorised Version C\d+\.\s*.*$', re.MULTILINE),
        re.compile(r'^\s*\d+\s+Taxation Administration Act 1953\s*$', re.MULTILINE), # Page numbers + act name
        re.compile(r'\f'), # Form feed characters
        re.compile(r'^\s*[\[\(]?\d+[\]\)]?\s*$', re.MULTILINE), # Standalone page numbers like - 1 - or (1)
        re.compile(r'^\s*[A-Za-z\s]+—[\s\w]+$', re.MULTILINE) # Running headers like "Part IIA—Assessments"
    ]

    for pattern in patterns:
        content = pattern.sub('', content)

    # Clean up multiple empty lines
    content = re.sub(r'\\n\\n\\n+', r'\\n\\n', content)
    content = content.strip() + '\\n' # Ensure a single newline at the end

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    base_dir = '/home/harrison/legislation-explorer/data/taa-1953/sections'
    modified_files = []

    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.md'):
                filepath = os.path.join(root, file)
                if cleanup_md_file(filepath):
                    modified_files.append(filepath)
    
    if modified_files:
        print("Modified files:")
        for f in modified_files:
            print(f)
    else:
        print("No files were modified.")

if __name__ == '__main__':
    main()
