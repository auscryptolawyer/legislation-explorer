
import json
import re
import os

def get_section_ids_from_tree(tree_path):
    with open(tree_path, 'r') as f:
        tree = json.load(f)

    section_ids = set()

    def _extract_ids_recursive(node):
        if 'id' in node and re.match(r'\d+[A-Z]?(-\d+[A-Z]?)?', node['id']):
            section_ids.add(node['id'])
        
        # Check for sections directly within the current node
        if 'sections' in node:
            for section in node['sections']:
                if 'id' in section and re.match(r'\d+[A-Z]?(-\d+[A-Z]?)?', section['id']):
                    section_ids.add(section['id'])

        # Recursively check children, divisions, and subdivisions
        if 'children' in node:
            for child in node['children']:
                _extract_ids_recursive(child)
        if 'divisions' in node:
            for division in node['divisions']:
                _extract_ids_recursive(division)
        if 'subdivisions' in node:
            for subdivision in node['subdivisions']:
                _extract_ids_recursive(subdivision)

    # Start traversal from the 'parts' key
    if 'parts' in tree:
        for part in tree['parts']:
            _extract_ids_recursive(part)
    return section_ids

def scan_raw_text_for_sections(raw_file_path, act_name):
    sections_in_raw = []

    # Define regex patterns based on act_name
    patterns = {
        "itaa-1997": [
            r"^(?P<section_id>\d+-\d+)\s+(?P<section_title>.+)",
            r"^Section\s+(?P<section_id>\d+-\d+)\s+(?P<section_title>.+)",
            r"^Subdivision\s+(?P<section_id>\d+-[A-Z]+)\s+(?P<section_title>.+)"
        ],
        "itaa-1936": [
            r"^(?P<section_id>\d+[A-Z]?)\s+(?P<section_title>.+)",
            r"^Section\s+(?P<section_id>\d+[A-Z]?)\s+(?P<section_title>.+)"
        ],
        "gst-1999": [
            r"^(?P<section_id>\d+-\d+)\s+(?P<section_title>.+)",
            r"^Section\s+(?P<section_id>\d+-\d+)\s+(?P<section_title>.+)"
        ],
        "taa-1953": [
            r"^(?P<section_id>\d+[A-Z]?)\s+(?P<section_title>.+)",
            r"^Section\s+(?P<section_id>\d+[A-Z]?)\s+(?P<section_title>.+)"
        ]
    }

    act_patterns = patterns.get(act_name, [])

    # Blacklist common act titles that can be false positives
    act_title_blacklist = [
        "Income Tax Assessment Act 1936",
        "Income Tax Assessment Act 1997",
        "A New Tax System (Goods and Services Tax) Act 1999",
        "Taxation Administration Act 1953",
        "Income Tax Assessment Act",
        "Taxation Administration Act"
    ]

    with open(raw_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f, 1):
            for pattern in act_patterns:
                match = re.match(pattern, line)
                if match:
                    section_id = match.group("section_id").strip()
                    section_title = match.group("section_title").strip()

                    # Filter out matches where the section title is a blacklisted act title
                    if section_title in act_title_blacklist:
                        continue

                    sections_in_raw.append({
                        "section_id": section_id,
                        "section_title_preview": section_title,
                        "raw_file": raw_file_path,
                        "line_number": i
                    })
                    break
    return sections_in_raw

def run_audit():
    acts = ["itaa-1936", "itaa-1997", "gst-1999", "taa-1953"]
    all_missing_sections_report = []
    
    base_path = "/home/harrison/legislation-explorer/data"
    
    for act in acts:
        print(f"Auditing {act}...")
        tree_path = os.path.join(base_path, act, "tree.json")
        raw_dir = os.path.join(base_path, act, "raw")

        if not os.path.exists(tree_path):
            print(f"  tree.json not found for {act} at {tree_path}. Skipping.")
            continue
        if not os.path.exists(raw_dir):
            print(f"  raw directory not found for {act} at {raw_dir}. Skipping.")
            continue

        tree_section_ids = get_section_ids_from_tree(tree_path)
        raw_text_sections = []

        for root, _, files in os.walk(raw_dir):
            for file in files:
                if file.endswith(".txt"):
                    raw_file_path = os.path.join(root, file)
                    raw_text_sections.extend(scan_raw_text_for_sections(raw_file_path, act))

        for section_in_raw in raw_text_sections:
            if section_in_raw["section_id"] not in tree_section_ids:
                all_missing_sections_report.append({
                    "act": act,
                    "missing_section_id": section_in_raw["section_id"],
                    "raw_file": section_in_raw["raw_file"],
                    "line_number": section_in_raw["line_number"],
                    "section_title_preview": section_in_raw["section_title_preview"]
                })
    
    output_path = "/home/harrison/legislation-explorer/data_quality_missing_sections.json"
    with open(output_path, 'w') as f:
        json.dump(all_missing_sections_report, f, indent=4)
    
    print(f"Audit complete. Results saved to {output_path}")

if __name__ == "__main__":
    run_audit()
