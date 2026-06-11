
import re
import os
import argparse

def clean_content(content):
    modified = False
    original_content = content
    cleaned_lines = []

    # --- Pattern 1: End-of-line concatenated headers ---
    header_patterns = [
        r"(Specialist liability rules Chapter [IVXLCDM]+(?:\s*Part\s*[IVXLCDM]+)?(?:\s*Division\s*[IVXLCDM]+)?)$",
        r"(General liability rules Chapter [IVXLCDM]+(?:\s*Part\s*[IVXLCDM]+)?(?:\s*Division\s*[IVXLCDM]+)?)$",
        r"(Introduction and core provisions Chapter [IVXLCDM]+(?:\s*Part\s*[IVXLCDM]+)?(?:\s*Division\s*[IVXLCDM]+)?)$",
        r"(Assessable income and exempt income Chapter [IVXLCDM]+(?:\s*Part\s*[IVXLCDM]+)?(?:\s*Division\s*[IVXLCDM]+)?)$",
        r"(Capital gains and losses: general topics Chapter [IVXLCDM]+(?:\s*Part\s*[IVXLCDM]+)?(?:\s*Division\s*[IVXLCDM]+)?)$",
        r"(Capital gains and losses: special topics Chapter [IVXLCDM]+(?:\s*Part\s*[IVXLCDM]+)?(?:\s*Division\s*[IVXLCDM]+)?)$",
        r"(Australian resident Chapter [IVXLCDM]+(?:\s*Part\s*[IVXLCDM]+)?(?:\s*Division\s*[IVXLCDM]+)?)$",
        r"(The Dictionary Chapter [IVXLCDM]+(?:\s*Part\s*[IVXLCDM]+)?(?:\s*Division\s*[IVXLCDM]+)?)$",
        r"(Resident of a Territory Chapter [IVXLCDM]+(?:\s*Part\s*[IVXLCDM]+)?(?:\s*Division\s*[IVXLCDM]+)?)$",
        r"(Deductions Chapter [IVXLCDM]+(?:\s*Part\s*[IVXLCDM]+)?(?:\s*Division\s*[IVXLCDM]+)?)$",
        r"(Trading stock Chapter [IVXLCDM]+(?:\s*Part\s*[IVXLCDM]+)?(?:\s*Division\s*[IVXLCDM]+)?)$",
        r"(Offsets Chapter [IVXLCDM]+(?:\s*Part\s*[IVXLCDM]+)?(?:\s*Division\s*[IVXLCDM]+)?)$",
        r"(Collection and recovery of income tax Chapter [IVXLCDM]+(?:\s*Part\s*[IVXLCDM]+)?(?:\s*Division\s*[IVXLCDM]+)?)$",
    ]
    generic_chapter_pattern = r"(.*? Chapter [IVXLCDM]+(?:\s*Part\s*[IVXLCDM]+)?(?:\s*Division\s*[IVXLCDM]+)?)$"
    header_patterns.append(generic_chapter_pattern)


    # --- Pattern 2: Standalone footer lines ---
    footer_patterns = [
        r"^Income Tax Assessment Act (1936|1997)\s+Page\s+\d+$",
        r"^Compilation No\.\s+\d+$",
        r"^Compilation date:\s+\d{2}/\d{2}/\d{4}$",
        r"^Authorised Version C\d{4}C\d{5,}\s+registered\s+\d{2}/\d{2}/\d{4}$",
        r"^(Page\s+)?\d+\s+Income Tax Assessment Act (1936|1997)$",
        r"^(Page\s+)?\d+\s+Treasury Laws Amendment \(Enhancing Superannuation Outcomes For Australians\) Act 2022(?:\s+Page\s+\d+)?$",
        r"^(Page\s+)?\d+\s+Treasury Laws Amendment \(More Flexible Superannuation\) Act 2021(?:\s+Page\s+\d+)?$",
        r"^(Page\s+)?\d+\s+Superannuation Guarantee \(Administration\) Act 1992(?:\s+Page\s+\d+)?$",
        r"^(Page\s+)?\d+\s+Treasury Laws Amendment \(2021 Measures No\. 6\) Act 2021(?:\s+Page\s+\d+)?$",
        r"^(Page\s+)?\d+\s+A New Tax System \(Australian Business Number\) Act 1999(?:\s+Page\s+\d+)?$",
        r"^(Page\s+)?\d+\s+Taxation Administration Act 1953(?:\s+Page\s+\d+)?$",
        r"^(Page\s+)?\d+\s+Fringe Benefits Tax Assessment Act 1986(?:\s+Page\s+\d+)?$",
        r"^(Page\s+)?\d+\s+A New Tax System \(Goods and Services Tax\) Act 1999(?:\s+Page\s+\d+)?$",
        r"^(Page\s+)?\d+\s+Retirement Savings Accounts Act 1997(?:\s+Page\s+\d+)?$"
    ]

    lines = content.splitlines()
    
    in_frontmatter = False
    frontmatter_end_index = -1

    # Detect frontmatter
    if lines and lines[0].strip() == '---':
        in_frontmatter = True
        cleaned_lines.append(lines[0]) # Keep the first '---'
        for i in range(1, len(lines)):
            cleaned_lines.append(lines[i])
            if lines[i].strip() == '---':
                in_frontmatter = False
                frontmatter_end_index = i
                break
    
    # Process content after frontmatter
    for i in range(frontmatter_end_index + 1, len(lines)):
        line = lines[i]
        
        # Apply header patterns (strip from the end)
        line_modified_by_header = False
        for pattern in header_patterns:
            # Use search to find the pattern anywhere in the line
            if re.search(pattern, line):
                # Replace only the matched pattern from the line
                new_line = re.sub(pattern, "", line).strip()
                if new_line != line:
                    line = new_line
                    modified = True
                    line_modified_by_header = True
                break # Only match one header pattern per line

        # Apply footer patterns (remove entire line)
        removed_by_footer = False
        for pattern in footer_patterns:
            if re.fullmatch(pattern, line.strip()):
                modified = True
                removed_by_footer = True
                break
        
        if not removed_by_footer:
            cleaned_lines.append(line)
        
    if modified:
        new_content = "\n".join(cleaned_lines).strip()
        # Add a final newline if the original content had one and it's not removed
        if original_content.endswith("\n") and not new_content.endswith("\n"):
            new_content += "\n"
        return new_content, True
    return original_content, False

def process_files(file_paths):
    modified_files_count = 0
    for md_file_path in file_paths:
        try:
            with open(md_file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            cleaned_content, changed = clean_content(content)

            if changed:
                with open(md_file_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                modified_files_count += 1
                # print(f"Modified: {md_file_path}")

        except Exception as e:
            print(f"Error processing {md_file_path}: {e}")
    return modified_files_count

def main():
    parser = argparse.ArgumentParser(description="Clean up garbled text in Markdown files.")
    parser.add_argument("file_paths", nargs='*', help="List of file paths to clean. If empty, scans standard paths.")
    args = parser.parse_args()

    if args.file_paths:
        md_files = args.file_paths
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        legislation_root = os.path.join(base_dir) # Should be /home/harrison/legislation-explorer
        data_dir = os.path.join(legislation_root, "data")
        
        md_files = []
        for root, _, files in os.walk(data_dir):
            for file in files:
                if file.endswith(".md") and "sections" in root:
                    md_files.append(os.path.join(root, file))

    print(f"Starting cleanup, found {len(md_files)} markdown files.")
    
    total_modified_files = process_files(md_files)

    print(f"Cleanup complete. Total files modified: {total_modified_files}")

if __name__ == "__main__":
    main()
