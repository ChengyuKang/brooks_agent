from typing import Any, Dict, List, Tuple
from langchain_chroma import Chroma

def _dedup_best_score(items: List[Tuple[float, Any]]) -> List[Tuple[float, Any]]:
    best = {}
    for score, doc in items:
        cid = (doc.metadata.get("chunk_id") or "").strip()
        if not cid:
            continue
        if cid not in best or score < best[cid][0]:
            best[cid] = (score, doc)
    return list(best.values())

def _where_and(filters: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Chroma 要求顶层只有一个 operator
    if len(filters) == 1:
        return filters[0]
    return {"$and": filters}

def _get_neighbors(db: Chroma, book: str, seq: int, neighbor_n: int):
    col = db._collection
    out = []
    for s in range(seq - neighbor_n, seq + neighbor_n + 1):
        if s < 0:
            continue
        res = col.get(
            where=_where_and([{"book": book}, {"seq": int(s)}]),
            include=["documents", "metadatas"],
        )
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []
        ids = res.get("ids") or []
        for d, m, i in zip(docs, metas, ids):
            out.append((d, m, i))
    return out

def _approx_tokens_from_meta(meta: Dict[str, Any], text: str) -> int:
    n = meta.get("n_tokens", 0)
    try:
        if int(n) > 0:
            return int(n)
    except Exception:
        pass
    return max(50, len(text) // 4)

def retrieve_with_plan(db: Chroma, plan) -> List[Any]:
    queries = plan.queries or [plan.query]
    all_hits: List[Tuple[float, Any]] = []

    for q in queries:
        q_book_list = plan.books
        extra_filters: List[Dict[str, Any]] = []

        if q.startswith("MGMT|"):
            q = q[len("MGMT|"):].strip()
            q_book_list = ["RANGE"]
            extra_filters = [{"part": "Part V: Orders and Trade Management"}]

        for book in q_book_list:
            k = int(plan.k_per_book.get(book, 4))
            where = _where_and([{"book": book}] + extra_filters)

            try:
                hits = db.similarity_search_with_score(q, k=k, filter=where)
            except TypeError:
                hits = db.similarity_search_with_score(q, k=k, where=where)

            # hits: [(Document, score)]
            for doc, score in hits:
                all_hits.append((float(score), doc))

    uniq = _dedup_best_score(all_hits)
    uniq.sort(key=lambda x: x[0])  # score 越小越相关

    # neighbor 扩展（只对 top_m）
    seen = set((doc.metadata.get("chunk_id") or "").strip() for _, doc in uniq)
    expanded_docs = []

    top_m = min(int(plan.expand_from_top_m), len(uniq))
    for _, doc in uniq[:top_m]:
        m = doc.metadata or {}
        book = (m.get("book") or "").upper()
        seq = m.get("seq")
        if not book or seq is None:
            continue

        for d_text, d_meta, _ in _get_neighbors(db, book, int(seq), int(plan.neighbor_n)):
            cid = (d_meta.get("chunk_id") or "").strip()
            if cid and cid not in seen:
                seen.add(cid)
                expanded_docs.append(type("Doc", (), {"page_content": d_text, "metadata": d_meta})())

    ordered_docs = [doc for _, doc in uniq] + expanded_docs

    # token budget 裁剪 + final_k
    final_docs = []
    used = 0
    for doc in ordered_docs:
        meta = doc.metadata or {}
        t = _approx_tokens_from_meta(meta, doc.page_content)
        if used + t > int(plan.token_budget):
            continue
        final_docs.append(doc)
        used += t
        if len(final_docs) >= int(plan.final_k):
            break

    return final_docs
