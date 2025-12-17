import json, argparse
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from ai_brooks_rag.decision_mapper import build_plan_from_decision_request
from ai_brooks_rag.retriever import retrieve_with_plan

load_dotenv()

PERSIST_DIR = "data/vector/chroma"
COLLECTION_NAME = "brooks_chunks_v1"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dr", required=True, help="path to a DecisionRequest json file")
    args = ap.parse_args()

    with open(args.dr, "r", encoding="utf-8") as f:
        dr = json.load(f)

    plan = build_plan_from_decision_request(dr)
    print("\n=== RetrievalPlan ===")
    print(json.dumps(plan.__dict__, indent=2, ensure_ascii=False))

    db = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=PERSIST_DIR,
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"),
    )

    docs = retrieve_with_plan(db, plan)
    print(f"\n=== Retrieved docs: {len(docs)} ===")
    for i, d in enumerate(docs, 1):
        m = d.metadata
        print("\n" + "-" * 90)
        print(f"[{i}] {m.get('book')} | seq={m.get('seq')} | pages {m.get('page_start')}-{m.get('page_end')}")
        print(f"chapter: {m.get('chapter')}")
        print(d.page_content[:700])

if __name__ == "__main__":
    main()
