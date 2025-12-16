from __future__ import annotations
import argparse
from pathlib import Path
from ai_brooks_knowledge.ingest_pipeline import build_page_items, build_chunks, write_jsonl

def parse_page_ranges(expr: str) -> set[int]:
    """
    "0-12,15,20-25" -> {0..12,15,20..25}
    """
    pages: set[int] = set()
    expr = (expr or "").strip()
    if not expr:
        return pages
    for part in expr.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            a, b = int(a), int(b)
            for i in range(min(a,b), max(a,b)+1):
                pages.add(i)
        else:
            pages.add(int(part))
    return pages

def run_one(book: str, pdf_path: str, exclude_expr: str, out_dir: Path, max_tokens: int, overlap: int, dry_run: bool):
    pdf = Path(pdf_path)
    hard_exclude = parse_page_ranges(exclude_expr)

    pages = build_page_items(book=book, pdf_path=pdf, hard_exclude_pages=hard_exclude)

    # 产出“页级中间产物”便于你检查：哪些页被判噪声、分数多少
    pages_jsonl = out_dir / "intermediate" / f"{book.lower()}_pages.jsonl"
    write_jsonl(pages_jsonl, (p.__dict__ for p in pages))

    print(f"[{book}] max_tokens={max_tokens} overlap={overlap}")
    if max_tokens < 300:
        raise ValueError("max_tokens too small; use 600-1000 for this project.")
    if overlap >= max_tokens * 0.35:
        raise ValueError("overlap too large; set overlap to ~10-20% of max_tokens (e.g., 80-160).")

    chunks = build_chunks(pages, max_tokens=max_tokens, overlap=overlap)
    chunks_jsonl = out_dir / "intermediate" / f"{book.lower()}_chunks.jsonl"
    write_jsonl(chunks_jsonl, (c.__dict__ for c in chunks))

    print(f"[{book}] pages_total={len(pages)} | pages_noise={sum(p.is_noise for p in pages)} | chunks={len(chunks)}")
    # dry_run 先到这里：你先验“清洗/切分/metadata”
    if dry_run:
        return

    # 下一步（Step 5）再加：embedding + FAISS 落盘
    # 这里先把骨架留好，避免你一次改太多导致不可控
    print(f"[{book}] dry_run=False but embedding/index is not implemented in this step yet.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trend")
    ap.add_argument("--range")
    ap.add_argument("--reversal")
    ap.add_argument("--trend-exclude", default="")
    ap.add_argument("--range-exclude", default="")
    ap.add_argument("--reversal-exclude", default="")
    ap.add_argument("--out-dir", default="data")
    ap.add_argument("--max-tokens", type=int, default=900)
    ap.add_argument("--overlap", type=int, default=120)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.trend:
        run_one("TREND", args.trend, args.trend_exclude, out_dir, args.max_tokens, args.overlap, args.dry_run)
    if args.range:
        run_one("RANGE", args.range, args.range_exclude, out_dir, args.max_tokens, args.overlap, args.dry_run)
    if args.reversal:
        run_one("REVERSAL", args.reversal, args.reversal_exclude, out_dir, args.max_tokens, args.overlap, args.dry_run)

if __name__ == "__main__":
    main()
