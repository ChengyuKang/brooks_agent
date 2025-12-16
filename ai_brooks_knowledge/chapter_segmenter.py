from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass
class MacroSection:
    title: str
    text: str
    start_page: int
    end_page: int


def _extract_heading(page_text: str) -> str | None:
    """Grab a plausible heading from the top of a page."""
    lines = [l.strip() for l in page_text.splitlines() if l.strip()]
    if not lines:
        return None

    first = lines[0]
    if re.match(r"^(chapter|part)\s+\d+", first, flags=re.IGNORECASE):
        return first
    if len(first.split()) <= 8 and first.isupper():
        return first.title()
    return None


def split_into_macro_sections(cleaned_pages: List[str]) -> List[MacroSection]:
    """
    Split pages into coarse sections using simple heading detection.
    Falls back to a single section if no headings are detected.
    """
    sections: List[MacroSection] = []
    current_lines: List[str] = []
    current_title = "Section 1"
    start_page = 1

    def flush(end_page: int):
        content = "\n\n".join(current_lines).strip()
        if content:
            sections.append(MacroSection(title=current_title, text=content, start_page=start_page, end_page=end_page))

    for idx, page in enumerate(cleaned_pages, start=1):
        if not page.strip():
            continue

        heading = _extract_heading(page)
        if heading and current_lines:
            flush(idx - 1)
            current_lines = [page]
            current_title = heading
            start_page = idx
        else:
            if heading and not current_lines:
                current_title = heading
            current_lines.append(page)

    flush(len(cleaned_pages))

    if not sections:
        merged = "\n\n".join(p for p in cleaned_pages if p.strip()).strip()
        if merged:
            sections.append(MacroSection(title="Section 1", text=merged, start_page=1, end_page=len(cleaned_pages)))

    return sections
