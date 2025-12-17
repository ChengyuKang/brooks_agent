from typing import Any, Dict, List, Tuple
import chromadb

def _dedup_by_chunk_id(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for r in rows:
        cid = r["metadata"].get("chunk_id")
        if cid and cid not in seen:
            seen.add(cid)
            out.append(r)
    return out

def search_book(
    collection,
    query_text: str,
    book: str,
    k: int,
) -> List[Dict[str, Any]]:
    # where 只做 book 过滤（v0.1 不依赖 chapter）
    res = collection.query(
        query_texts=[query_text],
        n_results=k,
        where={"book": book},
        include=["documents", "metadatas", "distances"],
    )
    docs = []
    for doc, md, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        docs.append({"text": doc, "metadata": md, "distance": dist})
    return docs

def fetch_neighbors(
    collection,
    book: str,
    seq: int,
    neighbor_n: int,
) -> List[Dict[str, Any]]:
    if neighbor_n <= 0:
        return []

    seqs = list(range(max(0, seq - neighbor_n), seq + neighbor_n + 1))
    out: List[Dict[str, Any]] = []

    # 尽量用 $in（如果你的 chromadb 版本不支持，会走 fallback）
    try:
        res = collection.get(
            where={"book": book, "seq": {"$in": seqs}},
            include=["documents", "metadatas"],
        )
        for doc, md in zip(res["documents"], res["metadatas"]):
            out.append({"text": doc, "metadata": md, "distance": None})
        return out
    except Exception:
        # fallback：逐个取
        for s in seqs:
            r = collection.get(
                where={"book": book, "seq": s},
                include=["documents", "metadatas"],
            )
            for doc, md in zip(r.get("documents", []), r.get("metadatas", [])):
                out.append({"text": doc, "metadata": md, "distance": None})
        return out

def retrieve_with_plan(
    persist_dir: str,
    collection_name: str,
    plan,
) -> List[Dict[str, Any]]:
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(collection_name)

    # 1) 分书检索
    candidates: List[Dict[str, Any]] = []
    for book in plan.books:
        k = plan.k_per_book.get(book, 6)
        candidates.extend(search_book(collection, plan.query, book, k))

    # 2) neighbor 扩展
    expanded: List[Dict[str, Any]] = []
    for c in candidates:
        md = c["metadata"]
        seq = md.get("seq")
        book = md.get("book")
        if isinstance(seq, int) and book:
            expanded.extend(fetch_neighbors(collection, book, seq, plan.neighbor_n))

    merged = _dedup_by_chunk_id(candidates + expanded)

    # 3)（可选）这里先不做 rerank，先返回给你测试
    return merged[: plan.final_k]
