import os, argparse
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# 可选：启用 query rewrite 才需要
try:
    from langchain_openai import ChatOpenAI
except Exception:
    ChatOpenAI = None

load_dotenv()

PERSIST_DIR = "data/vector/chroma"
COLLECTION_NAME = "brooks_chunks_v1"

BOOKS = ["TREND", "RANGE", "REVERSAL"]

@dataclass
class DecisionRequest:
    question: str
    regime: Optional[str] = None  # TREND / RANGE / REVERSAL
    extra: Optional[Dict[str, Any]] = None  # 以后塞你的 market snapshot 特征

def route_books(req: DecisionRequest) -> List[str]:
    r = (req.regime or "").upper().strip()
    if r in BOOKS:
        # 主书优先 + 另外两本兜底（避免主书没覆盖）
        others = [b for b in BOOKS if b != r]
        return [r] + others
    return BOOKS[:]  # 默认全搜

def rewrite_query(req: DecisionRequest, enable: bool) -> str:
    if not enable or ChatOpenAI is None:
        return req.question

    if not os.getenv("OPENAI_API_KEY"):
        return req.question

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)  # 你也可以换成你常用的
    sys = (
        "You rewrite user questions into concise, high-recall semantic search queries "
        "for a trading book knowledge base. Keep it short. Include key concepts, not filler."
    )
    user = f"""Original question:
{req.question}

Regime hint: {req.regime or "unknown"}

Return ONLY the rewritten search query."""
    out = llm.invoke([("system", sys), ("user", user)])
    q = (out.content or "").strip()
    return q if q else req.question

def get_neighbors_by_seq(db: Chroma, book: str, seqs: List[int]) -> List[Tuple[str, dict, str]]:
    """
    用底层 collection.get 通过 where 取回 (documents, metadatas, ids)
    返回 list of (doc_text, meta, id)
    """
    out = []
    col = db._collection  # Chroma 原生 collection
    for s in seqs:
        if s < 0:
            continue
        res = col.get(
            where={"$and": [{"book": book}, {"seq": int(s)}]},
            include=["documents", "metadatas"],  # ✅ ids 不要放 include
        )
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []
        ids = res.get("ids") or []              # ✅ ids 仍然会返回

        for d, m, i in zip(docs, metas, ids):
            out.append((d, m, i))
    return out

def retrieve(req: DecisionRequest, k_per_book: int, neighbor_window: int, enable_rewrite: bool):
    db = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=PERSIST_DIR,
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"),
    )

    routed_books = route_books(req)
    q = rewrite_query(req, enable_rewrite)

    # 1) book filter 检索（每本书取 k_per_book）
    base: List[Tuple[float, Any]] = []  # (score, Document)
    for b in routed_books:
        hits = db.similarity_search_with_score(q, k=k_per_book, filter={"book": b})

    for doc, score in hits:
        base.append((float(score), doc))

    # 2) 基础结果按 score 排序（Chroma 通常是 distance：越小越相似）
    base.sort(key=lambda x: x[0])

    # 3) neighbor 扩展：对 topN 做 seq±window
    seen_ids = set()
    final = []

    # 先放 base（去重）
    for score, doc in base:
        cid = (doc.metadata.get("chunk_id") or "").strip() or "UNKNOWN_ID"
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        final.append((score, doc))

    # 再扩 neighbors（按 base 的前若干个扩，避免爆炸）
    expand_from = final[: min(12, len(final))]  # 你可以调大/调小
    for _, doc in expand_from:
        m = doc.metadata or {}
        book = (m.get("book") or "").upper()
        seq = m.get("seq")
        if book not in BOOKS or seq is None:
            continue

        seq = int(seq)
        neigh_seqs = [seq + d for d in range(-neighbor_window, neighbor_window + 1) if d != 0]
        neigh_items = get_neighbors_by_seq(db, book, neigh_seqs)

        for d_text, d_meta, d_id in neigh_items:
            cid = (d_meta.get("chunk_id") or "").strip() or d_id
            if cid in seen_ids:
                continue
            seen_ids.add(cid)

            # 伪装成 Document 输出：用 db._collection.get 的结果不带 Document 类，这里简单复用 db.get 再取
            # 为了简洁：直接打印 neighbor 文本/元数据即可
            final.append((9999.0, type("Doc", (), {"page_content": d_text, "metadata": d_meta})()))

    # 4) 输出（按 book, seq 排序更像“连续阅读”）
    def sort_key(item):
        score, doc = item
        m = doc.metadata or {}
        return (m.get("book") or "", int(m.get("seq", 10**9)))

    final_sorted = sorted(final, key=sort_key)

    print("\n" + "=" * 90)
    print(f"Original Q : {req.question}")
    print(f"Rewritten Q: {q}")
    print(f"Route books: {routed_books}")
    print(f"Returned   : {len(final_sorted)} docs (base={len(base)}) neighbor_window={neighbor_window}")
    print("=" * 90)

    for i, (score, doc) in enumerate(final_sorted, 1):
        m = doc.metadata or {}
        print("\n" + "-" * 90)
        print(f"[{i}] {m.get('book')} | seq={m.get('seq')} | pages {m.get('page_start')}-{m.get('page_end')} | score={score}")
        print(f"chapter: {m.get('chapter')}")
        print(doc.page_content[:600])

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True)
    ap.add_argument("--regime", default="", help="TREND/RANGE/REVERSAL (optional)")
    ap.add_argument("--k-per-book", type=int, default=4)
    ap.add_argument("--neighbor", type=int, default=1)
    ap.add_argument("--rewrite", action="store_true", help="enable LLM query rewrite")
    return ap.parse_args()

def main():
    args = parse_args()
    req = DecisionRequest(question=args.query, regime=args.regime or None, extra=None)
    retrieve(req, k_per_book=args.k_per_book, neighbor_window=args.neighbor, enable_rewrite=args.rewrite)

if __name__ == "__main__":
    main()
