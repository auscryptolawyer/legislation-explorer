"""Verify the original bad data exists in the database."""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DEV_MODE'] = 'true'

from backend.services.tax_case_sql import _sql_dict

# Query raw data from case_citations for [2025] FCAFC 15
safe = "[2025] FCAFC 15".replace("'", "''")

# Get case_id
id_rows = _sql_dict(["id"], f"SELECT id FROM cases WHERE citation = '{safe}' LIMIT 1")
if not id_rows:
    print("Case not found")
    sys.exit(1)
case_id = id_rows[0]["id"]
cid_str = str(case_id)

# Raw citations from DB
raw_cites = _sql_dict(
    ["cited_citation", "paragraph_number"],
    f"SELECT cited_citation, paragraph_number FROM case_citations WHERE citing_case_id = '{cid_str}' ORDER BY paragraph_number"
)

print(f"=== RAW DATA FROM DB: {len(raw_cites)} total rows ===")
print()

# Self-citations
self_cites = [r for r in raw_cites if r.get('cited_citation') == '[2025] FCAFC 15']
print(f"Self-citations (cited_citation = '[2025] FCAFC 15'): {len(self_cites)}")
for r in self_cites:
    print(f"  cited_citation: {r.get('cited_citation')}, para: {r.get('paragraph_number')}")

# FCAC entries
fcac = [r for r in raw_cites if 'FCAC' in str(r.get('cited_citation', ''))]
print(f"\nFCAC entries: {len(fcac)}")
for r in fcac:
    print(f"  cited_citation: {r.get('cited_citation')}, para: {r.get('paragraph_number')}")

# AustLII chrome in paragraph_number
austlii_chrome = {'home', 'databases', 'worldlii', 'search', 'feedback',
    'database search', 'name search', 'recent decisions', 'noteup',
    'download', 'help', 'index', 'you are here', 'last updated', 'austlii',
    'print', 'email', 'full text', 'cookie', 'privacy', 'disclaimer', 'copyright'}
chrome = [r for r in raw_cites if r.get('paragraph_number') and str(r.get('paragraph_number')).strip().lower() in austlii_chrome]
print(f"\nAustLII chrome in paragraph_number: {len(chrome)}")
for r in chrome:
    print(f"  cited_citation: {r.get('cited_citation')}, para: {r.get('paragraph_number')}")

# Show all unique cited_citations
print(f"\n=== ALL UNIQUE CITED CITATIONS ({len(set(r.get('cited_citation') for r in raw_cites))}) ===")
for r in sorted(set(r.get('cited_citation') for r in raw_cites)):
    print(f"  {r}")

# Check legislation refs for chrome
leg_rows = _sql_dict(
    ["act_title", "section_reference", "paragraph_number"],
    f"SELECT act_title, section_reference, paragraph_number FROM case_legislation_refs WHERE case_id = '{cid_str}' ORDER BY paragraph_number"
)
chrome_leg = [r for r in leg_rows if r.get('paragraph_number') and str(r.get('paragraph_number')).strip().lower() in austlii_chrome]
print(f"\nAustLII chrome in legislation_refs paragraph_number: {len(chrome_leg)}")
for r in chrome_leg:
    print(f"  section: {r.get('section_reference')}, para: {r.get('paragraph_number')}")