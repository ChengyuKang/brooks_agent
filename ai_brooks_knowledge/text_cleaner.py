from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List, Set


def _normalize_line(line: str) -> str:
    """Collapse excessive whitespace for consistent comparisons."""
    return re.sub(r"\s+", " ", line.strip())


def _looks_like_page_number(line: str) -> bool:
    return bool(re.fullmatch(r"[ivxlcdmIVXLCDM]{1,6}|\d{1,4}", line.strip()))


def detect_repeated_header_footer_lines(
    raw_pages: List[str],
    top_k: int = 3,
    bottom_k: int = 3,
    freq_threshold: float = 0.6,
) -> Set[str]:
    """
    Identify lines that appear on a large share of pages (typical headers/footers).
    Returns a set of normalized lines to remove during cleaning.
    """
    top_counter: Counter[str] = Counter()
    bottom_counter: Counter[str] = Counter()

    for page in raw_pages:
        lines = page.splitlines()
        top_lines = [_normalize_line(l) for l in lines[:top_k] if l.strip()]
        bottom_lines = [_normalize_line(l) for l in lines[-bottom_k:] if l.strip()]
        top_counter.update(top_lines)
        bottom_counter.update(bottom_lines)

    total_pages = max(len(raw_pages), 1)
    min_freq = int(total_pages * freq_threshold)

    repeated = {line for line, cnt in top_counter.items() if cnt >= min_freq}
    repeated |= {line for line, cnt in bottom_counter.items() if cnt >= min_freq}
    return repeated


def clean_page_text(page_text: str, repeated_lines: Iterable[str] | None = None) -> str:
    """
    Remove detected headers/footers, obvious page numbers, and tidy whitespace.
    """
    if not page_text:
        return ""

    repeated = set(repeated_lines or [])
    text = page_text.replace("\u00ad", "")  # soft hyphen
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(\w)-\s*\n(\w)", r"\1\2", text)  # undo hyphenation across lines

    cleaned_lines: List[str] = []
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            if cleaned_lines and cleaned_lines[-1]:
                cleaned_lines.append("")  # paragraph break
            continue

        norm_line = _normalize_line(line)
        if norm_line in repeated:
            continue
        if _looks_like_page_number(norm_line):
            continue

        cleaned_lines.append(norm_line)

    cleaned = "\n".join(cleaned_lines).strip()
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned


def is_garbage_text(text: str) -> bool:
    """
    Heuristic to drop pages dominated by non-alphanumeric noise.
    """
    stripped = text.strip()
    if not stripped:
        return True
    if len(stripped) < 50:
        return False

    alnum = sum(ch.isalpha() or ch.isdigit() for ch in stripped)
    ratio = alnum / max(len(stripped), 1)
    weird = len(re.findall(r"[^\w\s.,;:?!'\"-]", stripped))
    if ratio < 0.25:
        return True
    if weird and (weird / len(stripped)) > 0.2:
        return True
    return False


def is_toc_or_index_like_page(text: str) -> bool:
    """
    Detect table-of-contents/index style pages: many dotted leader lines ending with numbers.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) < 5:
        return False

    toc_like = 0
    for line in lines:
        if re.search(r"\.{3,}\s*\d{1,4}$", line):
            toc_like += 1
        elif re.match(r"^(chapter|part)\s+\d+", line, flags=re.IGNORECASE):
            toc_like += 1

    if toc_like >= max(4, int(len(lines) * 0.5)):
        return True

    avg_len = sum(len(l) for l in lines) / max(len(lines), 1)
    return avg_len < 30 and toc_like >= 2
