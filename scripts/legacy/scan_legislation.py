
import re
import json
import os

def scan_file(filepath, contamination_patterns):
    contaminations = []
    act_name = extract_act_from_path(filepath)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            line_num = i + 1
            line_stripped = line.strip()

            # Pattern 1: Concatenated running headers at the end of lines
            for pattern_name, regex_pattern in contamination_patterns['running_header_concatenated'].items():
                if re.search(regex_pattern, line_stripped):
                    # Extract the actual appended garbage for suggested fix
                    match = re.search(regex_pattern, line_stripped)
                    garbage_string = line_stripped[match.start():]
                    contaminations.append({
                        'file_path': filepath,
                        'act': act_name,
                        'contamination_type': 'running_header_concatenated',
                        'example_lines': line_stripped[:150],
                        'line_numbers': [line_num],
                        'suggested_fix': f"Remove '{garbage_string}' from the end of the line.",
                        'pattern_matched': pattern_name
                    })

            # Pattern 2: Standalone footer lines
            for pattern_name, regex_pattern in contamination_patterns['footer_line'].items():
                if re.fullmatch(regex_pattern, line_stripped): # Use fullmatch for standalone lines
                    contaminations.append({
                        'file_path': filepath,
                        'act': act_name,
                        'contamination_type': 'footer_line',
                        'example_lines': line_stripped[:150],
                        'line_numbers': [line_num],
                        'suggested_fix': f"Remove this standalone footer line.",
                        'pattern_matched': pattern_name
                    })
            
            # Pattern 2: Form feed character (using '\f' as the literal character)
            if '\f' in line: # Check in the original line content, not stripped
                contaminations.append({
                    'file_path': filepath,
                    'act': act_name,
                    'contamination_type': 'form_feed',
                    'example_lines': line_stripped[:150],
                    'line_numbers': [line_num],
                    'suggested_fix': "Remove the form feed character '\\f'.",
                    'pattern_matched': 'form_feed_character'
                })

            # Pattern 3: Broken paragraph lines (simple heuristic)
            if i + 1 < len(lines):
                next_line_stripped = lines[i+1].strip()
                current_line_ends_mid_word = re.search(r'\b\w+$', line_stripped) and not line_stripped.endswith(('.', '!', '?', '-', '—', ';', ':', ','))
                
                next_line_starts_with_header = False
                for header_term in ['Chapter', 'Part', 'Division', 'Subdivision']:
                    # Check if the next line starts with a specific header term, case-insensitive
                    if re.match(re.escape(header_term) + r'\s+\d+\s*(\.?|\w+)', next_line_stripped, re.IGNORECASE) or \
                       re.match(re.escape(header_term) + r'\s+[A-Za-z]+\s*(\.?|\w+)', next_line_stripped, re.IGNORECASE):
                        next_line_starts_with_header = True
                        break
                
                if current_line_ends_mid_word and next_line_starts_with_header:
                     contaminations.append({
                        'file_path': filepath,
                        'act': act_name,
                        'contamination_type': 'broken_paragraph',
                        'example_lines': f"{line_stripped[:70]}...\\n...{next_line_stripped[:70]}", # Show part of both lines
                        'line_numbers': [line_num, line_num + 1],
                        'suggested_fix': "Merge with the next line and remove extraneous header if present.",
                        'pattern_matched': 'broken_paragraph_heuristic'
                    })

    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return contaminations

def extract_act_from_path(filepath):
    # Example path: /home/harrison/legislation-explorer/data/gst-1999/sections/chapter-04/...
    parts = filepath.split('/')
    if 'data' in parts:
        data_index = parts.index('data')
        if data_index + 1 < len(parts):
            act_folder = parts[data_index + 1]
            if '-' in act_folder:
                return act_folder.upper()
            else: # For acts like itaa-1997, itaa-1936
                return act_folder.replace('itaa-', 'ITAA').replace('gst-','GST').upper()
    return "Unknown Act"

def main():
    base_dir = "/home/harrison/legislation-explorer"
    all_md_files_path = "/tmp/hermes-results/tool_search_files_9cnFPCfd4IA7GFyjMiqD.txt"
    output_json_path = os.path.join(base_dir, "data_quality_garbled_detailed.json")
    
    # Initialize contamination patterns
    contamination_patterns_config = {
        'running_header_concatenated': {
            'Specialist liability rules Chapter': r'Specialist liability rules Chapter$',
            'General liability rules Chapter': r'General liability rules Chapter$',
            'Introduction and core provisions Chapter': r'Introduction and core provisions Chapter$',
            'Assessable income and exempt income Chapter': r'Assessable income and exempt income Chapter$',
            'Capital gains and losses: general topics Chapter': r'Capital gains and losses: general topics Chapter$',
            'Capital gains and losses: special topics Chapter': r'Capital gains and losses: special topics Chapter$',
            'Australian resident Chapter': r'Australian resident Chapter$',
            'The Dictionary Chapter': r'The Dictionary Chapter$',
            'Resident of a Territory Chapter': r'Resident of a Territory Chapter$',
            'Deductions Chapter': r'Deductions Chapter$',
            'Trading stock Chapter': r'Trading stock Chapter$',
            'Offsets Chapter': r'Offsets Chapter$',
            'Collection and recovery of income tax Chapter': r'Collection and recovery of income tax Chapter$',
            'Particular kinds of trusts Part': r'Particular kinds of trusts Part$',
            'Australian managed investment trusts Part': r'Australian managed investment trusts Part$',
            'Managed investment trusts Division': r'Managed investment trusts Division$',
            'Scrip for scrip roll-over Division': r'Scrip for scrip roll-over Division$',
            'Replacement-asset roll-overs Division': r'Replacement-asset roll-overs Division$',
        },
        'footer_line': {
            'Income Tax Assessment Act 1936': r'^\s*(\d+\s+)?Income Tax Assessment Act 1936(\s+\d+)?\s*$',
            'Income Tax Assessment Act 1997': r'^\s*(\d+\s+)?Income Tax Assessment Act 1997(\s+\d+)?\s*$',
            'Compilation No.': r'^\s*Compilation No\. \d+\s*$',
            'Compilation date:': r'^\s*Compilation date: \d{1,2}/\d{1,2}/\d{4}\s*$',
            'Authorised Version C registered': r'^\s*Authorised Version C\d+ registered \d{1,2}/\d{1,2}/\d{4}\s*$',
            'Authorised Version C': r'^\s*Authorised Version C\d+\s*$',
            'Page number + act name': r'^\s*\d+\s+(Income Tax Assessment Act 1936|Income Tax Assessment Act 1997)\s*$',
        }
    }

    all_contaminations = []
    md_files = []
    
    try:
        with open(all_md_files_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract the JSON object from the content string
            match = re.search(r'{.*}', content, re.DOTALL)
            if match:
                json_content = match.group(0)
                file_data = json.loads(json_content)
                md_files = file_data.get('files', [])
            else:
                print("Could not find JSON content in the file list.")
                return
    except Exception as e:
        print(f"Error loading and parsing file list: {e}")
        return

    print(f"Scanning {len(md_files)} Markdown files for garbled content...")

    for md_file in md_files:
        # Skip files that are not legislation content
        if md_file.startswith(os.path.join(base_dir, "backend")) or \
           md_file.startswith(os.path.join(base_dir, "DATA_QUALITY_AUDIT_PRD.md")) or \
           md_file.startswith(os.path.join(base_dir, "data_quality_parser_analysis.md")) or \
           md_file.startswith(os.path.join(base_dir, "TASKS.md")):
            continue
        all_contaminations.extend(scan_file(md_file, contamination_patterns_config))
    
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(all_contaminations, f, indent=2)

    print(f"Detailed contamination report saved to {output_json_path}")

    # Summary
    summary = {}
    for contamination in all_contaminations:
        contamination_type = contamination['contamination_type']
        act = contamination['act']
        
        if contamination_type not in summary:
            summary[contamination_type] = {}
        
        if act not in summary[contamination_type]:
            summary[contamination_type][act] = 0
            
        summary[contamination_type][act] += 1
    
    print("\n--- Summary of Contaminations ---")
    if not summary:
        print("No garbled content found.")
    else:
        for c_type, acts in summary.items():
            print(f"Contamination Type: {c_type}")
            for act, count in acts.items():
                print(f"  - {act}: {count} occurrences")
    print("---------------------------------")


if __name__ == "__main__":
    main()
