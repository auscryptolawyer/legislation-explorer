"""Test the CDN-0013 fix for get_case_references."""
import json
import sys
import os

# Add parent dir so 'backend' package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DEV_MODE'] = 'true'

from backend.services.case_db_service import get_case_references

refs = get_case_references('[2025] FCAFC 15')

case_citations = refs.get('case_citations', [])
cited_by = refs.get('cited_by', [])

# Check 1: No self-citations
self_cites = [c for c in case_citations if c.get('cited_citation') == '[2025] FCAFC 15']
self_cited_by = [c for c in cited_by if c.get('citation') == '[2025] FCAFC 15']

# Check 2: No AustLII chrome in paragraph_number
austlii_chrome = {'home', 'databases', 'worldlii', 'search', 'feedback',
    'database search', 'name search', 'recent decisions', 'noteup',
    'download', 'help', 'index', 'you are here', 'last updated', 'austlii',
    'print', 'email', 'full text', 'cookie', 'privacy', 'disclaimer', 'copyright'}
chrome_paras = [c.get('paragraph_number') for c in case_citations 
                if c.get('paragraph_number') and str(c.get('paragraph_number')).strip().lower() in austlii_chrome]

# Also check legislation refs
leg_refs = refs.get('legislation_refs', [])
chrome_leg_paras = [r.get('paragraph_number') for r in leg_refs
                    if r.get('paragraph_number') and str(r.get('paragraph_number')).strip().lower() in austlii_chrome]

# Check 3: No FCAC entries
fcac_entries = [c for c in case_citations if 'FCAC' in c.get('cited_citation', '')]

print("=== VERIFICATION RESULTS ===")
print(f"Total case_citations: {len(case_citations)}")
print(f"Total cited_by: {len(cited_by)}")
print(f"Total legislation_refs: {len(leg_refs)}")
print()
print(f"(a) Self-citations in case_citations: {len(self_cites)} {'PASS' if len(self_cites)==0 else 'FAIL'}")
print(f"(a) Self-citations in cited_by: {len(self_cited_by)} {'PASS' if len(self_cited_by)==0 else 'FAIL'}")
print()
print(f"(b) AustLII chrome in case_citations paragraph_number: {len(chrome_paras)} {'PASS' if len(chrome_paras)==0 else 'FAIL'}")
if chrome_paras:
    print(f"    Chrome values: {chrome_paras}")
print(f"(b) AustLII chrome in legislation_refs paragraph_number: {len(chrome_leg_paras)} {'PASS' if len(chrome_leg_paras)==0 else 'FAIL'}")
if chrome_leg_paras:
    print(f"    Chrome values: {chrome_leg_paras}")
print()
print(f"(c) FCAC entries: {len(fcac_entries)} {'PASS' if len(fcac_entries)==0 else 'FAIL'}")
if fcac_entries:
    print(f"    FCAC values: {[c.get('cited_citation') for c in fcac_entries]}")
print()

# Show sample data
print("=== SAMPLE CASE CITATIONS ===")
for c in case_citations[:5]:
    print(f"  cited_citation: {c.get('cited_citation')}, paragraph_number: {c.get('paragraph_number')}")

print()
print("=== CITED BY ===")
for c in cited_by[:5]:
    print(f"  citation: {c.get('citation')}, case_name: {c.get('case_name')}")

print()
print("=== SAMPLE LEGISLATION REFS ===")
for r in leg_refs[:5]:
    print(f"  act: {r.get('act_title')}, section: {r.get('section_reference')}, para: {r.get('paragraph_number')}")

# Summary
all_pass = (
    len(self_cites) == 0 and
    len(self_cited_by) == 0 and
    len(chrome_paras) == 0 and
    len(chrome_leg_paras) == 0 and
    len(fcac_entries) == 0
)
print(f"\n{'ALL CHECKS PASS' if all_pass else 'SOME CHECKS FAILED'}")