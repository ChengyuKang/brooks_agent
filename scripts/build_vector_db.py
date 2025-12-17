import os, glob, json, re
from tqdm import tqdm
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

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
    chapter_num = int(m.group(1)) if m else None

    meta = {
        "chunk_id": obj.get("chunk_id"),
        "book": obj.get("book"),
        "part": obj.get("part"),
        "chapter": chapter,
        "chapter_num": chapter_num,
        "page_start": int(obj.get("page_start", -1)),
        "page_end": int(obj.get("page_end", -1)),
        "pdf_path": obj.get("pdf_path"),
        "n_tokens": int(obj.get("n_tokens", -1)),
    }
    return text, meta

def stable_chunk_id(meta: dict, fallback_i: int) -> str:
    return meta.get("chunk_id") or f"fallback::{fallback_i}"

def make_text_for_embed(text: str, meta: dict) -> str:
    header = []
    if meta.get("book"): header.append(f"Book: {meta['book']}")
    if meta.get("chapter"): header.append(f"Chapter: {meta['chapter']}")
    if meta.get("part"): header.append(f"Part: {meta['part']}")
    if meta.get("page_start", -1) >= 0:
        header.append(f"Pages: {meta['page_start']}-{meta['page_end']}")
    return ("\n".join(header) + "\n\n" + text) if header else text

def load_all_jsonl(input_dir: str):
    paths = sorted(glob.glob(os.path.join(input_dir, "*.jsonl")))
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

def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set")

    rows = load_all_jsonl(INPUT_DIR)

    texts, metadatas, ids = [], [], []
    for i, obj in enumerate(rows):
        text, meta = extract_text_and_meta(obj)
        if not text:
            continue
        texts.append(make_text_for_embed(text, meta))
        metadatas.append(meta)
        ids.append(stable_chunk_id(meta, i))

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    db = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=PERSIST_DIR,
    )

    BATCH = 256
    for start in tqdm(range(0, len(texts), BATCH), desc="Upserting"):
        end = start + BATCH
        db.add_texts(texts=texts[start:end], metadatas=metadatas[start:end], ids=ids[start:end])

    print(f"✅ Done. chunks={len(texts)} saved to {PERSIST_DIR} / collection={COLLECTION_NAME}")

if __name__ == "__main__":
    main()
