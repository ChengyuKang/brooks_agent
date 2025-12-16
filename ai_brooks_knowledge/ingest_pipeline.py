from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import random

from PyPDF2 import PdfReader

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from .rag_config import CHUNK_SIZE, CHUNK_OVERLAP
from .text_cleaner import (
    detect_repeated_header_footer_lines,
    clean_page_text,
    is_toc_or_index_like_page,
    is_garbage_text,
)
from .chapter_segmenter import split_into_macro_sections


@dataclass
class BookSpec:
    name: str
    pdf_path: Path


def extract_raw_pages(pdf_path: Path, limit_pages: Optional[int] = None) -> List[str]:
    reader = PdfReader(str(pdf_path))
    total = len(reader.pages)
    n = min(total, limit_pages) if limit_pages else total
    return [(reader.pages[i].extract_text() or "") for i in range(n)]


def clean_pages_keep_alignment(raw_pages: List[str]) -> Tuple[List[str], dict]:
    repeated = detect_repeated_header_footer_lines(raw_pages)

    cleaned_pages: List[str] = []
    stats = {
        "total_pages": len(raw_pages),
        "empty_after_clean": 0,
        "filtered_toc_index": 0,
        "filtered_garbage": 0,
        "filtered_too_short": 0,
        "repeated_lines_count": len(repeated),
    }

    for raw in raw_pages:
        cleaned = clean_page_text(raw, repeated)

        if not cleaned.strip():
            cleaned_pages.append("")
            stats["empty_after_clean"] += 1
            continue

        if is_garbage_text(cleaned):
            cleaned_pages.append("")
            stats["filtered_garbage"] += 1
            continue

        if is_toc_or_index_like_page(cleaned):
            cleaned_pages.append("")
            stats["filtered_toc_index"] += 1
            continue

        if len(cleaned) < 200:
            cleaned_pages.append("")
            stats["filtered_too_short"] += 1
            continue

        cleaned_pages.append(cleaned)

    return cleaned_pages, stats


def build_macro_docs(cleaned_pages: List[str], book_name: str) -> List[Document]:
    sections = split_into_macro_sections(cleaned_pages)
    macro_docs: List[Document] = []

    for idx, sec in enumerate(sections):
        if len(sec.text) < 800:
            continue
        macro_docs.append(
            Document(
                page_content=sec.text,
                metadata={
                    "book": book_name,
                    "macro_title": sec.title,
                    "page_start": sec.start_page,
                    "page_end": sec.end_page,
                    "macro_id": idx,
                },
            )
        )

    return macro_docs


def build_micro_chunks(macro_docs: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", "!", "?", " "],
    )
    micro_docs = splitter.split_documents(macro_docs)

    for i, d in enumerate(micro_docs):
        d.metadata["chunk_id"] = i
        d.metadata["source"] = (
            f"{d.metadata.get('book','')}"
            f"|{d.metadata.get('macro_title','')}"
            f"|p{d.metadata.get('page_start','?')}-{d.metadata.get('page_end','?')}"
            f"|chunk{i}"
        )
    return micro_docs


def _print_debug_samples(book: BookSpec, raw_pages, cleaned_pages, macro_docs, micro_docs):
    print("\n================ DEBUG ================", flush=True)
    print(f"Book: {book.name}", flush=True)
    print(f"PDF : {book.pdf_path}", flush=True)

    sample_pages = [1, min(159, len(raw_pages)), min(318, len(raw_pages)), len(raw_pages)]
    for p in sample_pages:
        raw = (raw_pages[p - 1] or "").strip()
        cleaned = (cleaned_pages[p - 1] or "").strip()
        print(f"\n--- Page {p} RAW (first 250) ---", flush=True)
        print(raw[:250].replace("\n", "\\n"), flush=True)
        print(f"\n--- Page {p} CLEANED (first 250) ---", flush=True)
        print(cleaned[:250].replace("\n", "\\n"), flush=True)

    print("\n--- Macro sections (first 12) ---", flush=True)
    for d in macro_docs[:12]:
        print(
            f"  - {d.metadata.get('macro_title','')} "
            f"(p{d.metadata.get('page_start')}–{d.metadata.get('page_end')}) "
            f"chars={len(d.page_content)}",
            flush=True,
        )

    print("\n--- Micro chunks (random 5) ---", flush=True)
    if micro_docs:
        picks = random.sample(micro_docs, k=min(5, len(micro_docs)))
        for d in picks:
            txt = (d.page_content or "").strip()
            print(f"\n[{d.metadata.get('source','')}] chars={len(txt)}", flush=True)
            print(txt[:450].replace("\n", "\\n"), flush=True)

    print("\n======================================\n", flush=True)


def ingest_books(
    books: List[BookSpec],
    out_path: Path,
    limit_pages: Optional[int] = None,
    dry_run: bool = False,
    debug: bool = False,
):
    all_micro_docs: List[Document] = []

    for book in books:
        if not book.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {book.pdf_path}")

        print(f"\n➡️ Extracting pages: {book.pdf_path}", flush=True)
        raw_pages = extract_raw_pages(book.pdf_path, limit_pages=limit_pages)
        print(f"  Raw pages loaded: {len(raw_pages)}", flush=True)

        print("➡️ Cleaning pages...", flush=True)
        cleaned_pages, stats = clean_pages_keep_alignment(raw_pages)
        print(
            f"  Clean stats: total={stats['total_pages']} "
            f"empty_after_clean={stats['empty_after_clean']} "
            f"filtered_toc_index={stats['filtered_toc_index']} "
            f"filtered_garbage={stats['filtered_garbage']} "
            f"filtered_too_short={stats['filtered_too_short']} "
            f"repeated_lines={stats['repeated_lines_count']}",
            flush=True,
        )

        print("➡️ Macro split (Part/Chapter)...", flush=True)
        macro_docs = build_macro_docs(cleaned_pages, book.name)
        print(f"  Macro docs: {len(macro_docs)}", flush=True)

        print("➡️ Micro chunking...", flush=True)
        micro_docs = build_micro_chunks(macro_docs)
        print(f"  Micro chunks: {len(micro_docs)}", flush=True)

        all_micro_docs.extend(micro_docs)

        if debug:
            _print_debug_samples(book, raw_pages, cleaned_pages, macro_docs, micro_docs)

    print(f"\n✅ Total micro chunks across all books: {len(all_micro_docs)}", flush=True)

    if dry_run:
        print("\n🟡 DRY RUN: skipping embeddings + FAISS save.", flush=True)
        return

    print("\n➡️ Building embeddings + FAISS...", flush=True)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    vectorstore = FAISS.from_documents(all_micro_docs, embeddings)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(out_path))
    print(f"✅ FAISS saved to: {out_path}", flush=True)
