import os, json, re, argparse, shutil
from collections import defaultdict
from tqdm import tqdm
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

INPUT_DIR = "data/intermediate"
PERSIST_DIR = "data/vector/chroma"
COLLECTION_NAME = "brooks_chunks_v1"

_CH_NUM = re.compile(r"^Chapter\s+(\d+)\b", re.IGNORECASE)

def extract_text_and_meta(obj: dict):
    text = (obj.get("text") or "").strip()
    if not text:
        return "", {}

    chapter = obj.get("chapter") or ""
    m = _CH_NUM.search(chapter)
    chapter_num = int(m.group(1)) if m else -1  # 用 -1 避免 None

    meta = {
        "chunk_id": obj.get("chunk_id") or "",
        "book": obj.get("book") or "",
        "part": obj.get("part") or "",
        "chapter": chapter,
        "chapter_num": chapter_num,
        "page_start": int(obj.get("page_start", -1)),
        "page_end": int(obj.get("page_end", -1)),
        "pdf_path": obj.get("pdf_path") or "",
        "n_tokens": int(obj.get("n_tokens", -1)),
        # seq 会在后面按 book 排序后再写入
    }
    return text, meta

def stable_chunk_id(meta: dict, fallback_i: int) -> str:
    # Chroma 的 id 必须是字符串且稳定
    cid = meta.get("chunk_id") or ""
    return cid if cid else f"fallback::{fallback_i}"

def make_text_for_embed(text: str, meta: dict) -> str:
    header = []
    if meta.get("book"): header.append(f"Book: {meta['book']}")
    if meta.get("chapter"): header.append(f"Chapter: {meta['chapter']}")
    if meta.get("part"): header.append(f"Part: {meta['part']}")
    if meta.get("page_start", -1) >= 0:
        header.append(f"Pages: {meta['page_start']}-{meta['page_end']}")
    # 这里不把 seq 写进 embedding 文本（避免污染语义）；只放 metadata
    return ("\n".join(header) + "\n\n" + text) if header else text

def load_all_jsonl(input_dir: str):
    paths = []
    for name in ["trend_chunks.jsonl", "range_chunks.jsonl", "reversal_chunks.jsonl"]:
        p = os.path.join(input_dir, name)
        if os.path.exists(p):
            paths.append(p)

    if not paths:
        raise FileNotFoundError(f"No .jsonl files found in {input_dir}")

    rows = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows

def reset_persist_dir(persist_dir: str):
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)
    os.makedirs(persist_dir, exist_ok=True)

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default=INPUT_DIR)
    ap.add_argument("--persist-dir", default=PERSIST_DIR)
    ap.add_argument("--collection", default=COLLECTION_NAME)
    ap.add_argument("--reset", action="store_true", help="delete persist dir before building")
    ap.add_argument("--batch", type=int, default=256)
    return ap.parse_args()

def main():
    args = parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set")

    if args.reset:
        reset_persist_dir(args.persist_dir)

    rows = load_all_jsonl(args.input_dir)

    # 1) 先抽取并按 book 分组
    by_book = defaultdict(list)  # book -> list[(embed_text, meta, id)]
    skipped = 0
    for i, obj in enumerate(rows):
        text, meta = extract_text_and_meta(obj)
        if not text:
            skipped += 1
            continue

        book = meta.get("book") or "UNKNOWN"
        cid = stable_chunk_id(meta, i)
        embed_text = make_text_for_embed(text, meta)
        by_book[book].append((embed_text, meta, cid))

    # 2) 每个 book 内排序 → enumerate 写 seq → 汇总到最终 lists
    texts, metadatas, ids = [], [], []
    for book in sorted(by_book.keys()):
        items = by_book[book]

        items.sort(key=lambda x: (
            int(x[1].get("page_start", -1)),
            int(x[1].get("page_end", -1)),
            str(x[1].get("chunk_id") or x[2]),
        ))

        for seq, (embed_text, meta, cid) in enumerate(items):
            meta["seq"] = int(seq)                 # 核心：给 neighbor 扩展用
            meta["book_size"] = int(len(items))    # 可选：调试/质量控制用
            texts.append(embed_text)
            metadatas.append(meta)
            ids.append(cid)

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    db = Chroma(
        collection_name=args.collection,
        embedding_function=embeddings,
        persist_directory=args.persist_dir,
    )

    for start in tqdm(range(0, len(texts), args.batch), desc="Upserting"):
        end = start + args.batch
        db.add_texts(
            texts=texts[start:end],
            metadatas=metadatas[start:end],
            ids=ids[start:end],
        )

    print(f"✅ Done. chunks={len(texts)} skipped_empty={skipped}")
    print(f"   persist_dir={args.persist_dir}")
    print(f"   collection={args.collection}")

if __name__ == "__main__":
    main()
