
import json
import requests
import re
import os

def get_all_sections(base_path):
    all_sections = []
    act_dirs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    
    for act_dir in act_dirs:
        tree_file_path = os.path.join(base_path, act_dir, "tree.json")
        if not os.path.exists(tree_file_path):
            continue

        with open(tree_file_path, 'r') as f:
            tree_data = json.load(f)
            act_id = tree_data.get("act", act_dir.replace('-', ' ').upper()) # Use folder name if act is not directly in tree.json

            for part in tree_data.get("parts", []):
                for division in part.get("divisions", []):
                    for subdivision in division.get("subdivisions", []):
                        for section in subdivision.get("sections", []):
                            all_sections.append({
                                "act_id": act_id,
                                "section_id": section["id"],
                                "title": section["title"]
                            })
                    for section in division.get("sections", []):
                        all_sections.append({
                            "act_id": act_id,
                            "section_id": section["id"],
                            "title": section["title"]
                        })
                for section in part.get("sections", []):
                    all_sections.append({
                        "act_id": act_id,
                        "section_id": section["id"],
                        "title": section["title"]
                    })
    return all_sections

def audit_section(act_id, section_id):
    url = f"http://127.0.0.1:8765/api/section/{act_id}/{section_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        section_content = response.text
        
        broken_links = []
        
        # Pattern 1: Nested brackets: [*term [*other*](...)]
        # This will be tricky to catch with regex. It's more about semantic parsing.
        # Let's focus on simpler, more common malformed links for now.
        # This pattern implies a [text [more text](link)] type structure.
        # A simpler approach for now is to detect any unclosed brackets within a link text.
        pattern1 = r'\[[^\]]*\[.*?\]\(.*?\)' # Matches [text [inner_text](link)] - simplified

        # Pattern 2: Greedy period/semicolon in link: [*term.](/...) or [*term;](/...)
        pattern2 = r'\[\*(.*?)[.;]\*\]\((.*?)\)'
        
        # Pattern 3: Double bracket: [[*term*](/...)]
        pattern3 = r'\[\[(.*?)\]\((.*?)\)\]'
        
        # Pattern 4: Any link where the display text contains `[` or `]`
        pattern4_open_bracket = r'\[[^\]]*?\[.*?\]\(.*?\)'
        pattern4_close_bracket = r'\[[^\]]*?\].*?\]\(.*?\)'


        # Re-evaluating Pattern 1, 3, 4 to be more robust for the display text containing brackets
        # Let's generalize this pattern: any markdown link where the display text (the part inside [])
        # contains either an unescaped '[' or ']' character.
        # A markdown link generally looks like: [display text](url)
        # So we're looking for `[` or `]` within `display text`.

        # This regex attempts to find markdown links and then checks their display text
        # It's a two-step process: find all links, then check display text.
        # For simplicity, and given the prompt constraints, we'll try to catch directly.

        # General pattern for a markdown link: \[([^\]]+?)\]\((.*?)\)
        # We need to find `[` or `]` within the `([^\]]+?)` part.

        # Pattern for links with unescaped opening bracket in display text
        pattern_display_text_open_bracket = r'\[[^\]]*?\[.*?\]\(.*?\)'
        # Pattern for links with unescaped closing bracket in display text
        pattern_display_text_close_bracket = r'\[[^\]]*?\].*?\]\(.*?\)'


        # Let's simplify the regex for the patterns provided by the user.
        # The key is to find patterns *within the display text* of a markdown link.
        # A markdown link has the format [Display Text](URL).

        # 1. Nested brackets: `[*term [*other*](...)]`
        # This means the display text itself contains internal `[*...*]` or `[...]`
        # A regex for this would be looking for `\[[^\]]*?\[.*?\][^\]]*?\]\(.*?\)`
        # This specifically targets `[...[...]...](...)`
        re_pattern1 = r'\[([^\]]*?\[.*?\][^\]]*?)\]\((.*?)\)'
        matches1 = re.findall(re_pattern1, section_content)
        for text, url in matches1:
            broken_links.append(f"Nested brackets in display text: '[{text}]({url})'")

        # 2. Greedy period in link: `[*term.](/...)` or `[*term;](/...)`
        # This focuses on the display text ending with `.` or `;` immediately before the closing `]`.
        re_pattern2 = r'\[(\*[^\]]*?[.;]\*)\]\((.*?)\)'
        matches2 = re.findall(re_pattern2, section_content)
        for text, url in matches2:
            broken_links.append(f"Greedy period/semicolon in display text: '[{text}]({url})'")

        # 3. Double bracket: `[[*term*](/...)]`
        # This means the display text starts and/or ends with an extra bracket.
        re_pattern3 = r'\[\[(.*?)\]\((.*?)\)\]'
        matches3 = re.findall(re_pattern3, section_content)
        for text, url in matches3:
            broken_links.append(f"Double bracket around link text: '[{text}]({url})'")
            
        # 4. Any link where the display text contains `[` or `]`
        # This is a broader catch for unescaped brackets in the display text.
        # Need to be careful not to double count with pattern 1 & 3.
        # Let's find all markdown links first:
        all_markdown_links = re.findall(r'\[([^\]]+?)\]\((.*?)\)', section_content)
        for display_text, url in all_markdown_links:
            if '[' in display_text or ']' in display_text:
                # Make sure it's not already caught by pattern 1 or 3
                already_caught = False
                for t, u in matches1:
                    if t == display_text and u == url:
                        already_caught = True
                        break
                for t, u in matches3:
                    if t == display_text and u == url:
                        already_caught = True
                        break
                if not already_caught:
                    broken_links.append(f"Unescaped bracket in display text: '[{display_text}]({url})'")
        
        return broken_links

    except requests.exceptions.RequestException as e:
        return [f"API Error for {act_id}/{section_id}: {e}"]
    except Exception as e:
        return [f"General Error for {act_id}/{section_id}: {e}"]

def main():
    base_path = "/home/harrison/legislation-explorer/data"
    all_sections = get_all_sections(base_path)

    total_sections_checked = 0
    sections_with_broken_links = 0
    all_broken_instances = []

    print(f"Starting audit of {len(all_sections)} sections...")

    # Process in batches to print progress
    batch_size = 100
    for i in range(0, len(all_sections), batch_size):
        batch = all_sections[i:i + batch_size]
        print(f"Processing batch {int(i/batch_size) + 1}/{(len(all_sections) + batch_size - 1) // batch_size}...")
        for section in batch:
            total_sections_checked += 1
            act_id = section["act_id"]
            section_id = section["section_id"]
            
            broken_instances = audit_section(act_id, section_id)
            if broken_instances:
                sections_with_broken_links += 1
                for instance in broken_instances:
                    all_broken_instances.append({
                        "act": act_id,
                        "section": section_id,
                        "snippet": instance
                    })
        print(f"  Processed {total_sections_checked} sections. Found {sections_with_broken_links} sections with broken links so far.")

    print("\\n--- Audit Summary ---")
    print(f"Total sections checked: {total_sections_checked}")
    print(f"Sections with broken links: {sections_with_broken_links}")

    if all_broken_instances:
        print("Specific broken instances:")
        for item in all_broken_instances:
            print(f"- Act: {item['act']}, Section: {item['section']}, Issue: {item['snippet']}")
    else:
        print("No broken links found. Audit successful!")

    # Save results to a file for review
    with open("/home/harrison/legislation-explorer/audit_results.json", "w") as f:
        json.dump({
            "total_sections_checked": total_sections_checked,
            "sections_with_broken_links": sections_with_broken_links,
            "broken_instances": all_broken_instances,
            "success": sections_with_broken_links == 0
        }, f, indent=2)
    print("Audit results saved to /home/harrison/legislation-explorer/audit_results.json")

if __name__ == "__main__":
    main()
