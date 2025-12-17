from typing import Any, Dict, List, Tuple
from langchain_chroma import Chroma

def _dedup_best_score(items: List[Tuple[float, Any]]) -> List[Tuple[float, Any]]:
    """
    items: [(score, Document)] score 越小越相似
    去重策略：同 chunk_id 只保留 best(最小) score
    """
    best = {}
    for score, doc in items:
        cid = (doc.metadata.get("chunk_id") or "").strip()
        if not cid:
            continue
        if cid not in best or score < best[cid][0]:
            best[cid] = (score, doc)
    return list(best.values())

def _get_neighbors(db: Chroma, book: str, seq: int, neighbor_n: int):
    col = db._collection
    out = []
    for s in range(seq - neighbor_n, seq + neighbor_n + 1):
        if s < 0:
            continue
        res = col.get(
            where={"$and": [{"book": book}, {"seq": int(s)}]},
            include=["documents", "metadatas"],
        )
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []
        ids = res.get("ids") or []
        for d, m, i in zip(docs, metas, ids):
            out.append((d, m, i))
    return out

def _approx_tokens_from_meta(meta: Dict[str, Any]) -> int:
    # 你已经在 chunk.jsonl 里有 n_tokens，这里直接用（更稳定）
    n = meta.get("n_tokens", 0)
    try:
        return int(n)
    except Exception:
        return 0

def retrieve_with_plan(db: Chroma, plan) -> List[Any]:
    """
    返回 List[Document]，已做多 query 合并、neighbor 扩展、token budget 裁剪
    """
    queries = plan.queries or [plan.query]
    all_hits: List[Tuple[float, Any]] = []

    # 1) 多 query × 多 book 检索
    for q in queries:
        q_book_list = plan.books
        extra_filter = None

        if q.startswith("MGMT|"):
            q = q[len("MGMT|"):].strip()
            q_book_list = ["RANGE"]  # 强制只搜 RANGE
            extra_filter = {"part": "Part V: Orders and Trade Management"}  # 强制管理章节

        for book in q_book_list:
            k = int(plan.k_per_book.get(book, 4))
            f = {"book": book}
            if extra_filter:
                # book + extra_filter 用 $and 合并
                f = {"$and": [{"book": book}] + [{k: v} for k, v in extra_filter.items()]}
            else:
                f = {"book": book}

            hits = db.similarity_search_with_score(q, k=k, filter=f)
            for doc, score in hits:
                all_hits.append((float(score), doc))


    # 2) 去重（同 chunk_id 保留最相似）
    uniq = _dedup_best_score(all_hits)
    uniq.sort(key=lambda x: x[0])  # score 小的优先

    # 3) neighbor 扩展（只对 top_m 扩，避免爆炸）
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
                # 造一个“类 Document”
                expanded_docs.append(type("Doc", (), {"page_content": d_text, "metadata": d_meta})())

    # 4) 合并：原命中优先，然后邻居
    ordered_docs = [doc for _, doc in uniq] + expanded_docs

    # 5) token budget 裁剪（只裁动态 chunks；xinfa 以后单独处理）
    final_docs = []
    used = 0
    for doc in ordered_docs:
        meta = doc.metadata or {}
        t = _approx_tokens_from_meta(meta)
        if t <= 0:
            t = max(50, len(doc.page_content) // 4)

        if used + t > int(plan.token_budget):
            continue
        final_docs.append(doc)
        used += t
        if len(final_docs) >= int(plan.final_k):
            break

    return final_docs
