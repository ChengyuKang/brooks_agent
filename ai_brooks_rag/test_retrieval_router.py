import json
from dataclasses import asdict

from ai_brooks_rag.router import build_retrieval_plan
from ai_brooks_rag.retriever import retrieve_with_plan

# 你自己的：加载 snapshots / DecisionRequest 的方法
from data_loader import load_spy_5m_for_mvp
from ai_brooks_features.builder import build_market_snapshots
from decision_request import build_decision_request  # 你如果还没拆出来，就先写个函数返回 dict

PERSIST_DIR = "data/vector/chroma"
COLLECTION_NAME = "brooks_chunks"

def main():
    df = load_spy_5m_for_mvp(period="60d")
    snapshots = build_market_snapshots(df, symbol="SPY", timeframe_minutes=5, only_last_n_bars=None)

    while True:
        s = input("输入 snapshot index (q退出): ").strip()
        if s.lower() in ["q", "quit", "exit"]:
            break

        idx = int(s)
        snap = snapshots[idx]
        dr = build_decision_request(snapshot=snap, df=df)  # 你已有 bar_index，能取窗口

        plan = build_retrieval_plan(dr)
        print("\n=== RetrievalPlan ===")
        print(json.dumps(asdict(plan), indent=2, default=str))

        docs = retrieve_with_plan(PERSIST_DIR, COLLECTION_NAME, plan)
        print(f"\n=== Retrieved docs: {len(docs)} ===")
        for i, d in enumerate(docs):
            md = d["metadata"]
            title = f'{md.get("book")} | p{md.get("page_start")}-{md.get("page_end")} | seq={md.get("seq")}'
            print(f"\n--- [{i}] {title} ---")
            print(d["text"][:800])

if __name__ == "__main__":
    main()
