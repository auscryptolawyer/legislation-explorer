
import json
import os
import shutil

def find_duplicates_and_unknown_parts(tree_data):
    section_ids = {}
    duplicates = {}
    part_unknown_sections = []

    for part in tree_data['parts']:
        part_id = part['id']
        # Check sections directly under part
        for section in part.get('sections', []):
            sec_id = section['id']
            full_path = section['path']
            if sec_id in section_ids:
                if sec_id not in duplicates:
                    duplicates[sec_id] = [section_ids[sec_id]]
                duplicates[sec_id].append({'part_id': part_id, 'section_id': sec_id, 'title': section['title'], 'path': full_path})
            else:
                section_ids[sec_id] = {'part_id': part_id, 'section_id': sec_id, 'title': section['title'], 'path': full_path}
            
            if 'part-unknown' in full_path:
                part_unknown_sections.append({'part_id': part_id, 'section_id': sec_id, 'title': section['title'], 'path': full_path})

        # Check sections within divisions
        for division in part.get('divisions', []):
            division_id = division['id']
            for section in division.get('sections', []):
                sec_id = section['id']
                full_path = section['path']
                if sec_id in section_ids:
                    if sec_id not in duplicates:
                        duplicates[sec_id] = [section_ids[sec_id]]
                    duplicates[sec_id].append({'part_id': part_id, 'division_id': division_id, 'section_id': sec_id, 'title': section['title'], 'path': full_path})
                else:
                    section_ids[sec_id] = {'part_id': part_id, 'division_id': division_id, 'section_id': sec_id, 'title': section['title'], 'path': full_path}

                if 'part-unknown' in full_path:
                    part_unknown_sections.append({'part_id': part_id, 'division_id': division_id, 'section_id': sec_id, 'title': section['title'], 'path': full_path})
            
            # Check sections within subdivisions
            for subdivision in division.get('subdivisions', []):
                subdivision_id = subdivision['id']
                for section in subdivision.get('sections', []):
                    sec_id = section['id']
                    full_path = section['path']
                    if sec_id in section_ids:
                        if sec_id not in duplicates:
                            duplicates[sec_id] = [section_ids[sec_id]]
                        duplicates[sec_id].append({'part_id': part_id, 'division_id': division_id, 'subdivision_id': subdivision_id, 'section_id': sec_id, 'title': section['title'], 'path': full_path})
                    else:
                        section_ids[sec_id] = {'part_id': part_id, 'division_id': division_id, 'subdivision_id': subdivision_id, 'section_id': sec_id, 'title': section['title'], 'path': full_path}
                    
                    if 'part-unknown' in full_path:
                        part_unknown_sections.append({'part_id': part_id, 'division_id': division_id, 'subdivision_id': subdivision_id, 'section_id': sec_id, 'title': section['title'], 'path': full_path})

    return duplicates, part_unknown_sections

def clean_tree_and_files(tree_path, base_md_dir):
    with open(tree_path, 'r', encoding='utf-8') as f:
        tree_data = json.load(f)

    # --- Part B: Fix Duplicate Section IDs ---
    duplicates, _ = find_duplicates_and_unknown_parts(tree_data)
    
    modified_tree = tree_data
    sections_for_removal = []

    print("--- Analyzing Duplicate Section IDs ---")
    for sec_id, entries in duplicates.items():
        print(f"Duplicate ID: {sec_id}")
        for entry in entries:
            print(f"  - Part: {entry.get('part_id')}, Division: {entry.get('division_id', 'N/A')}, Section ID: {entry['section_id']}, Title: {entry['title']}, Path: {entry['path']}")
        
        # Heuristic: Remove duplicates that appear to be index/TOC entries, typically with simple numeric IDs and
        # located in part-iia (which from previous observation contains many such references)
        # and are not the 'primary' section of that ID.
        # This is a critical manual decision point based on the problem description.
        # For TAA 1953, sections like 1, 2, 3 in Part IIA referring to other Acts are likely the ones to remove.
        
        # Assuming the first occurrence is often the "primary" one in the main structure
        # We will remove subsequent occurrences if they are in 'IIA' and seem to be references.
        primary_entry = entries[0]
        for i in range(1, len(entries)):
            current_entry = entries[i]
            # Check if this duplicate entry seems to be a TOC/erroneous one.
            # Specifically targeting Part IIA for now as per observation.
            if current_entry.get('part_id') == 'IIA' and re.match(r'\d+', current_entry['section_id']):
                print(f"    -> Marking for removal (likely TOC/reference entry): Part: {current_entry.get('part_id')}, Section ID: {current_entry['section_id']}, Title: {current_entry['title']}, Path: {current_entry['path']}")
                sections_for_removal.append(current_entry)
            else:
                # If it's a real section with the same ID but different context (e.g., Schedule 1 vs main Act)
                # the instruction says to "note them but don't change unless clearly wrong".
                # For this task, I will not remove these.
                print(f"    -> Keeping (different parts/legitimate duplicate, as per instructions): Part: {current_entry.get('part_id')}, Section ID: {current_entry['section_id']}, Title: {current_entry['title']}, Path: {current_entry['path']}")

    # Apply removals
    removed_count = 0
    for removal_candidate in sections_for_removal:
        for part in modified_tree['parts']:
            if 'sections' in part:
                original_len = len(part['sections'])
                part['sections'] = [s for s in part['sections'] if not (s['id'] == removal_candidate['section_id'] and s.get('path') == removal_candidate['path'])]
                if len(part['sections']) < original_len:
                    removed_count += 1
                    # Also delete the associated markdown file
                    md_filepath = os.path.join(base_md_dir, removal_candidate['path'])
                    if os.path.exists(md_filepath):
                        os.remove(md_filepath)
                        print(f"Deleted MD file: {md_filepath}")

            if 'divisions' in part:
                for division in part['divisions']:
                    if 'sections' in division:
                        original_len = len(division['sections'])
                        division['sections'] = [s for s in division['sections'] if not (s['id'] == removal_candidate['section_id'] and s.get('path') == removal_candidate['path'])]
                        if len(division['sections']) < original_len:
                            removed_count += 1
                            md_filepath = os.path.join(base_md_dir, removal_candidate['path'])
                            if os.path.exists(md_filepath):
                                os.remove(md_filepath)
                                print(f"Deleted MD file: {md_filepath}")
                       
                    if 'subdivisions' in division:
                        for subdivision in division['subdivisions']:
                            if 'sections' in subdivision:
                                original_len = len(subdivision['sections'])
                                subdivision['sections'] = [s for s in subdivision['sections'] if not (s['id'] == removal_candidate['section_id'] and s.get('path') == removal_candidate['path'])]
                                if len(subdivision['sections']) < original_len:
                                    removed_count += 1
                                    md_filepath = os.path.join(base_md_dir, removal_candidate['path'])
                                    if os.path.exists(md_filepath):
                                        os.remove(md_filepath)
                                        print(f"Deleted MD file: {md_filepath}")

    print(f"Removed {removed_count} duplicate section entries from tree.json and their corresponding .md files.")
    
    # --- Part C: Fix part-unknown Paths ---
    _, part_unknown_sections_initial = find_duplicates_and_unknown_parts(tree_data) # Re-scan after removal

    fixed_path_count = 0
    file_moves = [] # List of (old_path, new_path) for files

    # Identify which divisions belong to Schedule 1
    # Common Schedule 1 divisions in TAA 1953 based on general knowledge and common patterns
    schedule_1_divisions = ['284', '355', '356', '268', '265', '295', '138', '110', '117', '342', '410', '384', '105', '382', '393', '269', '134'] # Add more as needed

    print("\n--- Fixing part-unknown paths ---")
    for part_info in part_unknown_sections_initial:
        original_path = part_info['path']
        path_parts = original_path.split('/')
        
        # Check against known Schedule 1 divisions
        # The structure is data/taa-1953/sections/part-unknown/division-XXX/YYY.md
        # We need to extract XXX to check if it's a Schedule 1 division.
        if len(path_parts) >= 4 and path_parts[2] == 'part-unknown':
            division_part = path_parts[3]
            if division_part.startswith('division-') and division_part.replace('division-', '') in schedule_1_divisions:
                new_part_name = 'schedule-1'
                new_path = original_path.replace('part-unknown', new_part_name)
                
                # Update the tree_data in place
                for part_tree in modified_tree['parts']:
                    # This logic only works if the part_id in tree.json is 'I', 'IA', etc.
                    # It does not cover a top-level 'schedule-1' part if it doesn't exist yet.
                    # The current structure has 'part-unknown' under part.id which is incorrect,
                    # so we need to add a 'schedule-1' part if not present.
                    pass # We will modify this part of the logic later after seeing the full structure.
                
                # For now, just track the changes for file moving and report.
                print(f"  - Original Path: {original_path} -> Suggested New Path: {new_path} (identified as Schedule 1)")
                
                # We need to find the specific section object in the tree and update its path
                # And its parent hierarchical structure if currently under an incorrect part
                found_and_updated = False
                for part_level in modified_tree['parts']:
                    part_sections = part_level.get('sections', [])
                    for s in part_sections:
                        if s.get('path') == original_path:
                            s['path'] = new_path
                            fixed_path_count += 1
                            file_moves.append((os.path.join(base_md_dir, original_path), os.path.join(base_md_dir, new_path)))
                            found_and_updated = True
                            break
                    if found_and_updated:
                        break

                    for division_level in part_level.get('divisions', []):
                        division_sections = division_level.get('sections', [])
                        for s in division_sections:
                            if s.get('path') == original_path:
                                s['path'] = new_path
                                fixed_path_count += 1
                                file_moves.append((os.path.join(base_md_dir, original_path), os.path.join(base_md_dir, new_path)))
                                found_and_updated = True
                                break
                        if found_and_updated:
                            break
                        
                        for subdivision_level in division_level.get('subdivisions', []):
                            subdivision_sections = subdivision_level.get('sections', [])
                            for s in subdivision_sections:
                                if s.get('path') == original_path:
                                    s['path'] = new_path
                                    fixed_path_count += 1
                                    file_moves.append((os.path.join(base_md_dir, original_path), os.path.join(base_md_dir, new_path)))
                                    found_and_updated = True
                                    break
                            if found_and_updated:
                                break
                    if found_and_updated:
                        break

    print(f"Fixed {fixed_path_count} part-unknown paths in tree.json.")
    
    # Execute file moves
    moved_files_count = 0
    for old_file, new_file in file_moves:
        os.makedirs(os.path.dirname(new_file), exist_ok=True)
        try:
            shutil.move(old_file, new_file)
            print(f"Moved file: {old_file} -> {new_file}")
            moved_files_count += 1
        except FileNotFoundError:
            print(f"Warning: File not found for move: {old_file}")

    # Save the modified tree.json
    with open(tree_path, 'w', encoding='utf-8') as f:
        json.dump(modified_tree, f, indent=2)
    print(f"Saved cleaned tree.json to {tree_path}")
    print(f"Executed {moved_files_count} file moves.")

if __name__ == '__main__':
    tree_file = '/home/harrison/legislation-explorer/data/taa-1953/tree.json'
    markdown_base_dir = '/home/harrison/legislation-explorer/data/taa-1953/sections'
    clean_tree_and_files(tree_file, markdown_base_dir)

