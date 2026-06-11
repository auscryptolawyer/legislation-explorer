
import os
import re

def clean_pdf_artifacts(content):
    # PDF artifacts to remove, mostly standalone lines
    patterns = [
        r"^A New Tax System \(Goods and Services Tax\) Act 1999\s*$",
        r"^Compilation No\. \d+\s*$",
        r"^Compilation date: \d{2}/\d{2}/\d{4}\s*$",
        r"^Authorised Version C\d+\.\s*$",
        r"^\s*\d+\s+A New Tax System \(Goods and Services Tax\) Act 1999\s*$", # Page numbers + act name
        r"\f", # Form feed characters
        r"^Part X-\d+ .*", # Running headers like Part X-Y <Title>
        r"^Division \d+ .*", # Running headers like Division X <Title>
    ]
    
    # Strip whitespace from each line too 
    lines = content.splitlines()
    cleaned_lines = []
    
    for line in lines:
        stripped_line = line.strip()
        discard = False
        for pattern in patterns:
            # Check if trimmed line is empty OR if the original line matches one of the cleanup patterns (including cases where the pattern might have leading/trailing spaces)
            if not stripped_line or re.match(pattern, line):
                discard = True
                break
        if not discard:
            cleaned_lines.append(stripped_line)
            
    # Remove consecutive blank lines
    filtered_lines = []
    for line in cleaned_lines:
        if not filtered_lines or line or filtered_lines[-1]: # Keep if line is not empty, or if previous line is not empty
            filtered_lines.append(line)
            
    return "\\n".join(filtered_lines)


def process_files(root_dir):
    modified_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".md"):
                filepath = os.path.join(dirpath, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                
                cleaned_content = clean_pdf_artifacts(content)
                
                if cleaned_content != content:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(cleaned_content)
                    modified_files.append(filepath)
    return modified_files

if __name__ == "__main__":
    script_dir = os.path.dirname(__file__)
    data_dir = os.path.join(script_dir, "data", "gst-1999", "sections")
    
    modified = process_files(data_dir)
    if modified:
        print("Cleaned PDF artifacts from the following files:")
        for f in modified:
            print(f)
    else:
        print("No files needed cleaning.")
