
import os
import re

def clean_itaa1936_file(filepath):
    """
    Cleans a single ITAA 1936 markdown file by removing PDF artifacts
    and normalizing blank lines.
    Returns True if the file was modified, False otherwise.
    """
    modified = False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False

    original_content_normalized = content.replace('\r\n', '\n') # Normalize newlines for consistent comparison
    lines = original_content_normalized.split('\n')
    
    # Regex patterns for standalone header/footer lines (remove entire line)
    standalone_patterns = [
        re.compile(r"^\s*Income Tax Assessment Act 1936\s*$"),
        re.compile(r"^\s*\d+\s+Income Tax Assessment Act 1936\s*$"), # Page number + act name
        re.compile(r"^\s*Income Tax Assessment Act 1936\s+\d+\s*$"), # Act name + page number
        re.compile(r"^\s*Compilation No\. \d+\s*$"),
        re.compile(r"^\s*Compilation date: \d{2}/\d{2}/\d{4}\s*$"),
        re.compile(r"^\s*Authorised Version C\d+\s+registered \d{2}/\d{2}/\d{4}\s*$"),
        re.compile(r"^\s*Authorised Version C\d+\s*$"),
        re.compile(r"^\f\s*$"), # Form feed character
        # Running headers (standalone lines) - patterns for entire line content
        re.compile(r"^\s*Part [IVX]+\s+.+?\s*$", re.IGNORECASE), # e.g. Part IV Returns and assessments
        re.compile(r"^\s*.+?\s+Part [IVX]+\s*$", re.IGNORECASE), # e.g. Returns and assessments Part IV
        re.compile(r"^\s*Section \d+[A-Z]?\s*$", re.IGNORECASE) # e.g. Section 170
    ]

    # Regex patterns for stripping contamination from the end of the line
    end_of_line_patterns = [
        re.compile(r"\s+Income Tax Assessment Act 1936\s+\d+\s*$", re.IGNORECASE),
        re.compile(r"\s+Section \d+[A-Z]?\s*$", re.IGNORECASE),
        re.compile(r"\s+Part [IVX]+\s*$", re.IGNORECASE),
        re.compile(r"\s+Authorised Version C\d+C?\d* registered \d{2}/\d{2}/\d{4}.*$", re.IGNORECASE)
    ]

    frontmatter_block = []
    body_block = []
    in_frontmatter = False
    frontmatter_end_found = False

    # Split frontmatter and body
    if lines and lines[0].strip() == '---':
        in_frontmatter = True
        frontmatter_block.append(lines[0])
        for line in lines[1:]:
            frontmatter_block.append(line)
            if line.strip() == '---':
                frontmatter_end_found = True
                in_frontmatter = False
                break
        
        if frontmatter_end_found:
            body_block = lines[len(frontmatter_block):]
        else: # Malformed frontmatter (no closing '---'), treat all as body
            frontmatter_block = [] # Reset frontmatter as it's not well-formed
            body_block = lines
    else: # No starting '---', treat all as body
        body_block = lines

    processed_body_lines = []
    for line in body_block:
        skip_line = False
        # Check for standalone patterns
        for pattern in standalone_patterns:
            if pattern.search(line):
                skip_line = True
                break
        
        if skip_line:
            continue

        # Check for end-of-line patterns and strip
        cleaned_line = line
        for pattern in end_of_line_patterns:
            cleaned_line = pattern.sub("", cleaned_line)
        processed_body_lines.append(cleaned_line)

    # Reassemble the body content from cleaned lines, then normalize blank lines
    temp_body_content = "\n".join(processed_body_lines)
    # Remove excessive blank lines (3+ newlines -> 2 newlines)
    final_body_content = re.sub(r'\n{3,}', '\n\n', temp_body_content)

    # Combine frontmatter and cleaned body
    new_content_parts = []
    if frontmatter_block:
        new_content_parts.extend(frontmatter_block)
        # If frontmatter was properly closed and there's body content, ensure separation
        if frontmatter_end_found and final_body_content.strip():
            new_content_parts.append("") # Adds one blank line

    if final_body_content:
        new_content_parts.append(final_body_content)
    
    new_content = "\n".join(new_content_parts)

    # Ensure content ends with a single newline if it's not empty, for consistency
    if new_content and not new_content.endswith('\n'):
        new_content += '\n'
    if original_content_normalized and not original_content_normalized.endswith('\n'):
        original_content_normalized += '\n'
    elif not original_content_normalized and new_content: # Handle case of empty original content becoming non-empty
        original_content_normalized = '\n' # Or compare against ""

    if new_content != original_content_normalized:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            modified = True
        except Exception as e:
            print(f"Error writing to {filepath}: {e}")
    
    return modified


def main():
    base_dir = '/home/harrison/legislation-explorer'
    target_dir = os.path.join(base_dir, 'data', 'itaa-1936', 'sections')
    
    if not os.path.isdir(target_dir):
        print(f"Error: Target directory not found: {target_dir}")
        return

    modified_files_count = 0
    print(f"Starting cleanup in '{target_dir}'...")

    for root, _, files in os.walk(target_dir):
        for filename in files:
            if filename.endswith('.md'):
                filepath = os.path.join(root, filename)
                if clean_itaa1936_file(filepath):
                    modified_files_count += 1
                    # print(f"Modified: {filepath}") # Uncomment for debugging
    
    print(f"Cleanup complete. Total files modified: {modified_files_count}.")

if __name__ == '__main__':
    main()
