#!/usr/bin/env python3
"""Extract narrative sections from SEC 10-K HTML filings.

Pulls just the qualitative content that structured data (XBRL/MCP) can't provide:
- Item 1: Business overview
- Item 1A: Risk Factors
- Item 1C: Cybersecurity (brief)
- Item 2: Properties
- Item 7: MD&A
- Item 7A: Market Risk

Skips financial tables, XBRL tags, legal boilerplate, and governance sections.

Usage:
    python3 extract_10k_narrative.py <input.htm> <output.txt> [--ticker TICKER]
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


def find_item_sections(text):
    """Find the start positions of each Item section (content, not TOC)."""
    sections = {}
    target_items = {
        '1': 'Business',
        '1A': 'Risk Factors',
        '1C': 'Cybersecurity',
        '2': 'Properties',
        '7': 'MD&A',
        '7A': 'Market Risk',
    }

    for item_num, label in target_items.items():
        # Match "ITEM 1." or "ITEM 1A." — use word boundary after the number
        # to prevent "ITEM 1" from matching "ITEM 1A"
        if item_num[-1].isalpha():
            pattern = rf'ITEM\s+{re.escape(item_num)}[\.\s]'
        else:
            pattern = rf'ITEM\s+{re.escape(item_num)}(?![A-Z])[\.\s]'
        matches = list(re.finditer(pattern, text, re.IGNORECASE))

        # The TOC entry is short (just title + page number).
        # The actual content section is followed by paragraphs of text.
        # Heuristic: look at the next 1000 chars — content sections have
        # long runs of text, TOC entries have other "ITEM" headings nearby.
        for m in matches:
            after = text[m.start():m.start() + 1000]
            # Count how many other ITEM headings appear in the next 1000 chars
            other_items = len(re.findall(r'ITEM\s+\d', after[50:], re.IGNORECASE))
            # TOC has many Item headings clustered together; content has 0-1
            if other_items <= 1:
                heading = re.sub(r'\s+', ' ', after[:200].split('\n')[0]).strip()
                sections[item_num] = {
                    'start': m.start(),
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
        print("Usage: python3 extract_10k_narrative.py <input.htm> <output.txt> [--ticker TICKER]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    ticker = "UNKNOWN"
    if "--ticker" in sys.argv:
        idx = sys.argv.index("--ticker")
        if idx + 1 < len(sys.argv):
            ticker = sys.argv[idx + 1]

    print(f"Reading {input_path}...")
    with open(input_path, 'r', errors='replace') as f:
        html = f.read()

    print("Stripping HTML...")
    text = html_to_text(html)

    print("Finding sections...")
    sections = find_item_sections(text)

    if not sections:
        print("ERROR: Could not find any Item sections in the filing.")
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
    output_parts.append(f"# {ticker} — 10-K Narrative Sections (Curated)")
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
