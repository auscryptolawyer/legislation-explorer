"""Text cleaning utilities for case paragraphs and ruling bodies."""

from __future__ import annotations

import re

# ── AustLII navigation noise ────────────────────────────────────────────────

_AUSTLII_NAV_LINES: list[re.Pattern] = [
    re.compile(r'^(Home|Databases|WorldLII|Search|Feedback)\s*$', re.IGNORECASE),
    re.compile(r'^(Database Search|Name Search|Recent Decisions)\s*$', re.IGNORECASE),
    re.compile(r'^\[(Noteup|Download|Help)\]\s*$'),
    re.compile(r'^\[?(You are here|Last Updated)\s*:.*$', re.IGNORECASE),
    re.compile(r'^AustLII\s*:?\s*$', re.IGNORECASE),
    re.compile(r'^\*\s+AustLII:\s*$'),
    re.compile(r'^\*{3,}\s*$'),  # horizontal rule-like
    re.compile(r'^-{3,}\s*$'),   # horizontal rule-like
    re.compile(r'^={3,}\s*$'),   # horizontal rule-like
    re.compile(r'^[|+\-*]{8,}\s*$'),  # decorative borders
]

_AUSTLII_SUB_PATTERNS = [
    (re.compile(r'\s*\[Noteup\]\s*'), ' '),
    (re.compile(r'\s*\[Download\]\s*'), ' '),
    (re.compile(r'\s*\[Help\]\s*'), ' '),
    (re.compile(r'\s*\[Home\]\s*'), ' '),
    (re.compile(r'\s*\[Databases\]\s*'), ' '),
    (re.compile(r'\s*\[WorldLII\]\s*'), ' '),
    (re.compile(r'\s*\[Search\]\s*'), ' '),
    (re.compile(r'\s*\[Feedback\]\s*'), ' '),
    (re.compile(r'\s*\[Database Search\]\s*'), ' '),
    (re.compile(r'\s*\[Name Search\]\s*'), ' '),
    (re.compile(r'\s*\[Recent Decisions\]\s*'), ' '),
    (re.compile(r'\s*\[Index\]\s*'), ' '),
    (re.compile(r'\s*Last Updated:\s*[^\]]*\]?', re.IGNORECASE), ' '),
    (re.compile(r'\s*You are here:\s*[^\]]*\]?', re.IGNORECASE), ' '),
]


# Patterns for footnote-only lines (short citation references, not judgment text)
_FOOTNOTE_PATTERNS = [
    re.compile(r'^\(\d{4}\)\s+\d+\s+\w+\s+\d+'),  # (2003) 212 CLR 511.
    re.compile(r'^\[\d{4}\]\s+\w+\s+\d+'),  # [1984] HCA 61
    re.compile(r'^\d+\s+IR\s+\d+'),  # 334 IR 70
    re.compile(r'^\d+\s+NSWLR\s+\d+'),  # 117 NSWLR 253
    re.compile(r'^\d+\s+ALR\s+\d+'),  # 212 ALR 1
    re.compile(r'^\d+\s+ALJR\s+\d+'),  # 90 ALJR 1
    re.compile(r'^\d+\s+FCR\s+\d+'),  # 150 FCR 1
    re.compile(r'^\d+\s+A\s+W+N+\s+\(NSW\)\s+\d+'),  # 92 WN (NSW) 1070
    re.compile(r'^See\s+(also\s+)?our\s+reasons'),  # "See our reasons at [13], [16]"
    re.compile(r'^See\s+[A-Z]'),  # "See Santayana..."
]

_AUSTLII_SHORT_LINE_RE = re.compile(
    r'^(AustLII:|Copyright Policy|Disclaimers|Privacy Policy|Feedback)',
    re.IGNORECASE
)


def clean_case_paragraph(content: str) -> str:
    """Strip AustLII navigation noise and footnote-only lines from a paragraph.

    Removes lines that are purely navigation UI elements, and scrubs
    stray markers from within text. Returns empty string if the entire
    paragraph is noise.
    """
    lines = content.splitlines()
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip pure navigation lines
        skip = any(p.match(stripped) for p in _AUSTLII_NAV_LINES)
        if skip:
            continue
        # Skip AustLII header boilerplate (Date of order, High Court of Australia HCA #, etc.)
        if any(p.search(stripped) for p in _AUSTLII_HEADER_LINES):
            continue
        # Skip short footnote-only lines
        stub = stripped.rstrip('.')
        if len(stub) < 80 and any(p.match(stub) for p in _FOOTNOTE_PATTERNS):
            continue
        if _AUSTLII_SHORT_LINE_RE.match(stripped):
            continue
        cleaned.append(line)
    result = '\n'.join(cleaned)

    # Remove inline markers
    for pattern, replacement in _AUSTLII_SUB_PATTERNS:
        result = pattern.sub(replacement, result)

    # Collapse multiple blank lines and trim
    result = re.sub(r'\n{3,}', '\n\n', result).strip()

    # Merge fragmented sentences: if a line starts lowercase / comma,
    # and prev line isn't empty and isn't a heading, join them
    merged_lines = []
    out_lines = result.splitlines()
    for line in out_lines:
        stripped = line.strip()
        if not stripped:
            merged_lines.append('')
            continue
        if merged_lines and merged_lines[-1]:
            prev = merged_lines[-1]
            if (stripped[0].islower() or stripped.startswith(',')) and not prev.startswith('#'):
                merged_lines[-1] = prev.rstrip() + ' ' + stripped
                continue
        merged_lines.append(stripped)
    result = '\n'.join(merged_lines)

    return result


# ── ATO ruling noise ────────────────────────────────────────────────────────

_ATO_NAV_LINES: list[re.Pattern] = [
    re.compile(r'^Legal database\s*$', re.IGNORECASE),
    re.compile(r'^(Contents|Download|Email|Print|Para)\s*$', re.IGNORECASE),
    re.compile(r'^Back to browse\s*$', re.IGNORECASE),
    re.compile(r'^\d+\s+related documents\s*$'),
    re.compile(r'^PDF version', re.IGNORECASE),
    re.compile(r'^is the authorised', re.IGNORECASE),
    re.compile(r'^There is a Compendium', re.IGNORECASE),
    re.compile(r'^Please note that the', re.IGNORECASE),
    re.compile(r'^This document incorporates revisions', re.IGNORECASE),
    re.compile(r'^View its history and amending notices', re.IGNORECASE),
    re.compile(r'^You are here\s*', re.IGNORECASE),
    re.compile(r'^Back to top\s*$', re.IGNORECASE),
    re.compile(r'^©\s*AUSTRALIAN TAXATION OFFICE', re.IGNORECASE),
    re.compile(r'^You are free to copy', re.IGNORECASE),
    re.compile(r'^(Taxation Ruling|Taxation Determination)\s*$', re.IGNORECASE),
    re.compile(r'^(Commissioner of Taxation)\s*$'),
    re.compile(r'^Previously released in draft form', re.IGNORECASE),
    re.compile(r'^[A-Z]{2,6}\s+\d{4}/\d+\s*$'),  # standalone citation like "TR 2020/1"
    re.compile(r'^[A-Z]{2,6}\s+\d{4}/\d+EC\s*$'),  # "TR 2020/1EC"
    re.compile(r'^ato\.gov\.au\s*$', re.IGNORECASE),
    re.compile(r'^history\s*$', re.IGNORECASE),
    re.compile(r'^and amending notices', re.IGNORECASE),
    re.compile(r'^\d+\s*$'),  # standalone digit(s) (TOC page number)
    re.compile(r'^\.\s*$'),  # standalone period
    re.compile(r'^\*{3,}\s*$'),
    re.compile(r'^-{3,}\s*$'),
    re.compile(r'^={3,}\s*$'),
]

_DESCRIPTIVE_TITLE_RE = re.compile(
    r'(?:TR\s+\d{4}/\d+|TD\s+\d{4}/\d+|SGR\s+\d{4}/\d+|GSTR\s+\d{4}/\d+'
    r'|PCG\s+\d{4}/\d+|LCG\s+\d{4}/\d+|MT\s+\d{4}/\d+|IT\s+\d+'
    r'|PS\s+LA\s+\d{4}/\d+|TA\s+\d{4}/\d+)\s*\n\s*(.+?)(?:\n\s*\n|$)',
    re.DOTALL
)

# Also match standalone descriptive title line (when citation heading was stripped)
_DESCRIPTIVE_TITLE_STANDALONE = re.compile(r'^[A-Z][a-z]+:\s+.+')

# AustLII case header boilerplate — text that's just the case title, citation, date, court
# These appear as the first 1-3 paragraphs and contain no judgment text
_AUSTLII_HEADER_LINES: list[re.Pattern] = [
    re.compile(r'Date of order:\s*\d+\s+\w+\s+\d+', re.IGNORECASE),
    re.compile(r'Date of pub', re.IGNORECASE),
    re.compile(r'High Court of Australia\s+HCA\s+\d+'),
    re.compile(r'Federal Court of Australia\s+FCA'),
    re.compile(r'Full Court of the Federal Court\s+FCAFC'),
]

_BOLD_CLEAN = re.compile(r'\*\*([^*]+)\*\*')


def clean_ruling_body(body: str) -> dict:
    """Strip ATO navigation noise from a ruling body.

    * Removes navigation lines (Legal database, Contents, Download, …)
    * Extracts the **descriptive title** (the multi-line text after the citation heading)
    * Converts section headers to ## markdown headings for ToC support
    * Returns ``{body: str, descriptive_title: str}``
    """
    lines = body.splitlines()
    cleaned: list[str] = []
    descriptive_title = ''

    # Extract descriptive title: lines after the citation heading
    # until a blank line or known ATO navigation pattern
    citation_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r'^(TR|TD|SGR|GSTR|PCG|LCG|MT|IT|PS LA|TA)\s+\d', stripped, re.IGNORECASE):
            citation_idx = i
            break

    if citation_idx is not None:
        title_lines = []
        for j in range(citation_idx + 1, min(citation_idx + 10, len(lines))):
            s = lines[j].strip()
            if not s:
                break
            # Stop at ATO navigation patterns
            if any(p.match(s) for p in [
                re.compile(r'^Please note that the', re.IGNORECASE),
                re.compile(r'^PDF version', re.IGNORECASE),
                re.compile(r'^There is a Compendium', re.IGNORECASE),
                re.compile(r'^Legal database', re.IGNORECASE),
                re.compile(r'^Contents', re.IGNORECASE),
                re.compile(r'^This document incorporates', re.IGNORECASE),
            ]):
                break
            title_lines.append(s)
        if title_lines:
            descriptive_title = ' '.join(title_lines)

    # Section header patterns — lines that should become ## headings
    # These are standalone lines that are NOT numbered paragraphs or bullet points
    _SECTION_HEADER_RE = re.compile(
        r'^(Summary|Ruling|Date of effect|Introduction|Background|'
        r'Purpose and context|Explanation|'
        r'Detailed analysis|Examples?|Application|'
        r'Commissioner of Taxation|'
        r'Relying on this Ruling|'
        r'Elements of|Importance of|Relevance of|'
        r'The negative tests|Capital or capital|Private or domestic|'
        r'Gaining or producing exempt|Substantiation|'
        r'Exceptions and relief|'
        r'Appendix\s+\d+|'
        r'Work-related|'
        r'Not legally binding|Legally binding)',
        re.IGNORECASE
    )

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip pure navigation lines
        skip = any(p.match(stripped) for p in _ATO_NAV_LINES)
        if skip:
            continue
        # Convert section headers to ## headings (but not numbered paragraphs)
        if (_SECTION_HEADER_RE.match(stripped)
                and not re.match(r'^\d+[\.\)]', stripped)
                and not stripped.startswith('•')
                and len(stripped) < 80):
            cleaned.append(f'## {stripped}')
            continue
        cleaned.append(line)

    result = '\n'.join(cleaned)

    # Collapse multiple blank lines
    result = re.sub(r'\n{3,}', '\n\n', result)

    # Strip bold formatting from non-emphasis uses
    result = _BOLD_CLEAN.sub(r'\1', result)

    result = result.strip()
    return {'body': result, 'descriptive_title': descriptive_title}
