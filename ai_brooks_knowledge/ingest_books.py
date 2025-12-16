from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from .rag_config import BROOKS_FAISS_PATH
from .ingest_pipeline import BookSpec, ingest_books  # ✅ 关键：从 pipeline 导出


def parse_args():
    p = argparse.ArgumentParser(description="Ingest Brooks books into FAISS (clean + macro split + micro chunk).")
    p.add_argument("--trend", type=str, required=True, help="Path to trend1.pdf")
    p.add_argument("--range", type=str, default=None, help="Path to range2.pdf")
    p.add_argument("--reversal", type=str, default=None, help="Path to reversal3.pdf")
    p.add_argument("--out", type=str, default=str(BROOKS_FAISS_PATH), help="Output FAISS directory path")
    p.add_argument("--limit-pages", type=int, default=None, help="Only process first N pages of each PDF (testing)")
    p.add_argument("--dry-run", action="store_true", help="Skip embeddings/save; only test extraction/clean/chunk")
    p.add_argument("--debug", action="store_true", help="Print debug samples")
    return p.parse_args()


def main():
    args = parse_args()

    books: List[BookSpec] = [BookSpec("Trading Price Action Trends", Path(args.trend))]
    if args.range:
        books.append(BookSpec("Trading Price Action Trading Ranges", Path(args.range)))
    if args.reversal:
        books.append(BookSpec("Trading Price Action Reversals", Path(args.reversal)))

    ingest_books(
        books=books,
        out_path=Path(args.out),
        limit_pages=args.limit_pages,
        dry_run=args.dry_run,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
