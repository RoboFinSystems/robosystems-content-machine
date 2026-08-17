#!/usr/bin/env python3
"""Extract narrative sections from SEC 10-K / 10-Q HTML filings.

Pulls just the qualitative content that structured data (XBRL/MCP) can't provide.

10-K (default): Item 1 Business, 1A Risk Factors, 1C Cybersecurity, 2 Properties,
7 MD&A, 7A Market Risk.

10-Q (--form 10-Q): Item 2 MD&A, Item 3 Market Risk, and Part II Item 1A Risk
Factors. Item numbers do NOT carry their 10-K meanings in a 10-Q, so running the
default mode over a 10-Q labels the financial statements "Business" and the MD&A
"Properties" - wrong in a way downstream authoring will quote verbatim.

Section boundaries are heuristic. On filings that lay headings out unusually a
section can come back drastically short, so CHECK THE REPORTED WORD COUNTS and
fall back to --full, which skips detection and emits the whole cleaned filing.
An oversized source file is a nuisance; a silently truncated one gets wrong
numbers published.

Skips financial tables, XBRL tags, legal boilerplate, and governance sections.

Usage:
    python3 extract_10k_narrative.py <in.htm> <out.txt> [--ticker T] [--form 10-K|10-Q] [--full]
"""

import re
import sys
from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):
    """Strip HTML tags, preserving meaningful whitespace."""

    def __init__(self):
        super().__init__()
        self.text = []
        self._skip = False
        self._skip_tags = {"script", "style", "ix:header"}

    def handle_starttag(self, tag, attrs):
        tag_lower = tag.lower()
        if tag_lower in self._skip_tags:
            self._skip = True
        # Add newlines for block elements
        if tag_lower in ("p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.text.append("\n")
        if tag_lower == "td":
            self.text.append("\t")

    def handle_endtag(self, tag):
        if tag.lower() in self._skip_tags:
            self._skip = False
        if tag.lower() in ("p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table"):
            self.text.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.text.append(data)

    def get_text(self):
        return "".join(self.text)


def html_to_text(html_content):
    """Convert HTML to clean text."""
    extractor = HTMLTextExtractor()
    extractor.feed(html_content)
    return extractor.get_text()


def clean_text(text):
    """Clean up extracted text — collapse whitespace, remove junk."""
    # Remove XBRL-style data blobs (long strings of identifiers)
    text = re.sub(r'[a-z]{2,10}:[A-Z][A-Za-z0-9]+Member', '', text)
    text = re.sub(r'\d{10,}', '', text)  # Remove long number strings (CIK-like)

    # Collapse multiple blank lines to max 2
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

    # Collapse multiple spaces/tabs
    text = re.sub(r'[ \t]+', ' ', text)

    # Remove lines that are just whitespace or page numbers
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip empty lines (but keep paragraph breaks via logic below)
        if not stripped:
            if cleaned and cleaned[-1] != '':
                cleaned.append('')
            continue
        # Skip page numbers
        if re.match(r'^\d{1,3}$', stripped):
            continue
        # Skip "Table of Contents" links
        if stripped.lower() == 'table of contents':
            continue
        cleaned.append(stripped)

    return '\n'.join(cleaned)


# Item numbers mean different things in a 10-K and a 10-Q. In a 10-Q, Item 1 is
# the financial statements and Item 2 is the MD&A — labelling those "Business" and
# "Properties" (the 10-K meanings) hands downstream authoring a mis-sourced quote.
FORM_SECTIONS = {
    '10-K': {
        '1': 'Business',
        '1A': 'Risk Factors',
        '1C': 'Cybersecurity',
        '2': 'Properties',
        '7': 'MD&A',
        '7A': 'Market Risk',
    },
    '10-Q': {
        # Part I
        '2': 'MD&A',
        '3': 'Market Risk',
        # Part II — searched after the PART II boundary (see find_item_sections)
        '1A': 'Risk Factors',
    },
}

# Part II items must be located after the PART II heading; the same item numbers
# also appear in Part I with different meanings.
PART_II_ITEMS = {'10-Q': {'1A'}}


def find_item_sections(text, form='10-K'):
    """Find the start positions of each Item section (content, not TOC)."""
    sections = {}
    target_items = FORM_SECTIONS.get(form, FORM_SECTIONS['10-K'])
    part_ii_items = PART_II_ITEMS.get(form, set())

    # Locate the PART II boundary so Part II items aren't matched against Part I.
    part_ii_pos = 0
    for m in re.finditer(r'(?:^|\n)\s*(?:PART|Part)\s+II\b', text):
        after = text[m.start():m.start() + 1000]
        if len(re.findall(r'ITEM\s+\d', after[50:], re.IGNORECASE)) <= 1:
            part_ii_pos = m.start()
            break

    for item_num, label in target_items.items():
        # Match "ITEM 1." or "ITEM 1A." — use word boundary after the number
        # to prevent "ITEM 1" from matching "ITEM 1A".
        if item_num[-1].isalpha():
            body = rf'ITEM\s+{re.escape(item_num)}[\.\s]'
        else:
            body = rf'ITEM\s+{re.escape(item_num)}(?![A-Z])[\.\s]'
        # A real heading starts a line. Anchoring rejects inline cross-references
        # such as 'see Item 1A of our Annual Report on Form 10-K', which otherwise
        # match and capture a forward-looking-statements paragraph instead.
        matches = list(re.finditer(rf'(?:^|\n)[ \t]*({body})', text, re.IGNORECASE))
        if not matches:  # fall back to unanchored for filings with odd whitespace
            matches = list(re.finditer(rf'({body})', text, re.IGNORECASE))

        floor = part_ii_pos if item_num in part_ii_items else 0

        # The TOC entry is short (just title + page number).
        # The actual content section is followed by paragraphs of text.
        # Heuristic: look at the next 1000 chars — content sections have
        # long runs of text, TOC entries have other "ITEM" headings nearby.
        for m in matches:
            pos = m.start(1)
            if pos < floor:
                continue
            after = text[pos:pos + 1000]
            # Count how many other ITEM headings appear in the next 1000 chars
            other_items = len(re.findall(r'ITEM\s+\d', after[50:], re.IGNORECASE))
            # In a 10-Q, "Item 1A ... of our Annual Report on Form 10-K" is a pointer at
            # a DIFFERENT filing, and matching it captures a forward-looking-statements
            # paragraph instead of the risk factors. Only a 10-Q can make this mistake;
            # in a 10-K the same phrase is self-referential and must not be rejected.
            if form == '10-Q' and re.search(
                    r'Annual\s+Report\s+on\s+Form\s+10-K', after[:300], re.IGNORECASE):
                continue
            # TOC has many Item headings clustered together; content has 0-1
            if other_items <= 1:
                heading = re.sub(r'\s+', ' ', after[:200].split('\n')[0]).strip()
                sections[item_num] = {
                    'start': pos,
                    'label': label,
                    'heading': heading
                }
                break

    return sections


def extract_section(text, start, next_start):
    """Extract text between two positions, with cleanup."""
    section = text[start:next_start]
    return clean_text(section)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 extract_10k_narrative.py <input.htm> <output.txt> [--ticker TICKER] [--full] [--form 10-K|10-Q]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    ticker = "UNKNOWN"
    if "--ticker" in sys.argv:
        idx = sys.argv.index("--ticker")
        if idx + 1 < len(sys.argv):
            ticker = sys.argv[idx + 1]
    form = "10-K"
    if "--form" in sys.argv:
        idx = sys.argv.index("--form")
        if idx + 1 < len(sys.argv):
            form = sys.argv[idx + 1].upper()
    if form not in FORM_SECTIONS:
        print(f"ERROR: unsupported --form {form} (expected one of {', '.join(FORM_SECTIONS)})")
        sys.exit(1)

    print(f"Reading {input_path}...")
    with open(input_path, 'r', errors='replace') as f:
        html = f.read()

    print("Stripping HTML...")
    text = html_to_text(html)

    # --full skips section detection entirely. Section boundaries are heuristic and
    # can silently drop most of an MD&A on filings that lay their headings out oddly;
    # a too-large source file is a nuisance, a silently truncated one gets bad numbers
    # published. Prefer --full whenever the sections look short.
    if "--full" in sys.argv:
        full = clean_text(text)
        with open(output_path, 'w') as f:
            f.write(f"# {ticker} — {form} full text (no section extraction)\n")
            f.write("# Financial tables are included here; prefer XBRL via RoboSystems MCP for figures.\n\n")
            f.write(full)
        print(f"\nTotal: {len(full.split()):,} words → {output_path}")
        return

    print(f"Finding sections ({form})...")
    sections = find_item_sections(text, form)

    if not sections:
        print("ERROR: Could not find any Item sections in the filing.")
        print("Re-run with --full to dump the whole filing instead.")
        sys.exit(1)

    # Sort sections by position
    sorted_items = sorted(sections.items(), key=lambda x: x[1]['start'])

    # Build list of ALL major Item heading positions to use as boundaries.
    # Match "Item N." or "ITEM N." at start of line — excludes inline refs
    # like 'see Item 1A. "Risk Factors"' which appear mid-paragraph.
    all_item_positions = []
    for m in re.finditer(r'(?:^|\n)\s*(?:Item|ITEM)\s+\d+[A-Z]?\.', text):
        all_item_positions.append(m.start())
    # Also include PART headings as boundaries
    for m in re.finditer(r'(?:^|\n)\s*(?:PART|Part)\s+[IV]+\b', text):
        all_item_positions.append(m.start())
    all_item_positions.append(len(text))
    all_item_positions.sort()

    print(f"\nFound {len(sections)} narrative sections:")
    for item_num, info in sorted_items:
        print(f"  Item {item_num}: {info['label']} (pos {info['start']})")

    # Extract each section
    output_parts = []
    output_parts.append(f"# {ticker} — {form} Narrative Sections (Curated)")
    output_parts.append(f"# Auto-extracted from SEC filing — qualitative content only")
    output_parts.append(f"# Financial tables and XBRL data excluded (available via RoboSystems MCP)")
    output_parts.append("")

    total_words = 0
    for item_num, info in sorted_items:
        start = info['start']
        # Find the next Item start after this one
        next_starts = [p for p in all_item_positions if p > start + 100]
        if next_starts:
            end = next_starts[0]
        else:
            end = len(text)

        section_text = extract_section(text, start, end)

        # Trim overly long sections (risk factors can be 50+ pages)
        words = len(section_text.split())
        if words > 8000 and item_num == '1A':
            # For risk factors, keep first ~6000 words + note truncation
            truncated = ' '.join(section_text.split()[:6000])
            last_para = truncated.rfind('\n\n')
            if last_para > 0:
                truncated = truncated[:last_para]
            section_text = truncated + "\n\n[... Risk factors truncated for brevity — see full 10-K for complete list ...]"
            words = len(section_text.split())

        total_words += words
        output_parts.append(f"{'='*80}")
        output_parts.append(f"## Item {item_num}: {info['label']}")
        output_parts.append(f"{'='*80}")
        output_parts.append("")
        output_parts.append(section_text)
        output_parts.append("")

        print(f"  Extracted Item {item_num}: {words:,} words")

    # Write output
    output = '\n'.join(output_parts)
    with open(output_path, 'w') as f:
        f.write(output)

    print(f"\nTotal: {total_words:,} words → {output_path}")


if __name__ == "__main__":
    main()
