# ai_brooks_knowledge/pdf_qa.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple
from collections import Counter
import re
import hashlib

from PyPDF2 import PdfReader


@dataclass
class PageStat:
    page: int
    n_chars: int
    n_lines: int
    empty: bool
    weird_char_ratio: float
    has_link: bool


_WEIRD_RE = re.compile(r"[^\x09\x0a\x0d\x20-\x7E]")  # 非常粗的“非ASCII”检测
_LINK_RE = re.compile(r"https?://|www\.", re.IGNORECASE)


def extract_pages_pypdf2(pdf_path: str) -> List[str]:
    print(f"Extracting pages from PDF: {pdf_path}")
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append(text)
    return pages


def compute_page_stats(pages: List[str]) -> List[PageStat]:
    stats: List[PageStat] = []
    for i, t in enumerate(pages):
        s = t.strip()
        n_chars = len(s)
        lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
        n_lines = len(lines)
        empty = (n_chars == 0)
        weird = len(_WEIRD_RE.findall(s))
        weird_ratio = (weird / max(1, n_chars))
        has_link = bool(_LINK_RE.search(s))
        stats.append(PageStat(
            page=i+1,
            n_chars=n_chars,
            n_lines=n_lines,
            empty=empty,
            weird_char_ratio=weird_ratio,
            has_link=has_link,
        ))
    return stats


def find_repeated_header_footer_lines(pages: List[str], top_k: int = 2, bottom_k: int = 2) -> Counter:
    c = Counter()
    for t in pages:
        lines = [ln.strip() for ln in (t or "").splitlines() if ln.strip()]
        for ln in lines[:top_k]:
            c[ln] += 1
        for ln in lines[-bottom_k:]:
            c[ln] += 1
    return c


def report_pdf_quality(pdf_path: str, max_print: int = 10):
    pages = extract_pages_pypdf2(pdf_path)
    stats = compute_page_stats(pages)

    total = len(stats)
    empty = sum(1 for s in stats if s.empty)
    low = sum(1 for s in stats if s.n_chars < 100)
    links = sum(1 for s in stats if s.has_link)
    weird_hi = sum(1 for s in stats if s.weird_char_ratio > 0.02)

    print("PDF:", pdf_path)
    print(f"Total pages: {total}")
    print(f"Empty pages: {empty} ({empty/total:.1%})")
    print(f"Low-text pages (<100 chars): {low} ({low/total:.1%})")
    print(f"Pages containing links: {links} ({links/total:.1%})")
    print(f"Pages with high weird-char ratio (>2%): {weird_hi} ({weird_hi/total:.1%})")

    rep = find_repeated_header_footer_lines(pages, top_k=2, bottom_k=2)
    common = rep.most_common(max_print)
    print("\nMost common header/footer candidate lines:")
    for ln, cnt in common:
        if cnt < int(0.5 * total):
            break
        preview = (ln[:120] + "…") if len(ln) > 120 else ln
        print(f"  ({cnt}/{total}) {preview}")

    # 抽样打印若干页开头用于人工检查
    print("\nSample page snippets:")
    for idx in [1, total//3, 2*total//3, total]:
        t = pages[idx-1].strip()
        snippet = t[:500].replace("\n", "\\n")
        print(f"  Page {idx}: {snippet} ...")


if __name__ == "__main__":
    import sys
    report_pdf_quality(sys.argv[1])
