from __future__ import annotations
import argparse
import re
from pathlib import Path
import fitz  # PyMuPDF

def extract_page_text(pdf_path: Path, page_index: int) -> str:
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_index)
    text = page.get_text("text") or ""
    doc.close()
    # 统一换行
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=15)
    args = ap.parse_args()

    pdf_path = Path(args.pdf)
    doc = fitz.open(pdf_path)
    total = doc.page_count
    doc.close()

    print(f"[PDF] {pdf_path} | total_pages={total}")
    start = max(0, args.start)
    end = min(total, args.end)

    for i in range(start, end):
        raw = extract_page_text(pdf_path, i)
        snippet = re.sub(r"\s+", " ", raw).strip()[:500]
        print(f"\n--- page_index={i} ---")
        print(snippet if snippet else "(empty)")

if __name__ == "__main__":
    main()
