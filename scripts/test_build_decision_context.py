import json, argparse
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from ai_brooks_rag.decision_mapper import build_plan_from_decision_request
from ai_brooks_rag.retriever import retrieve_with_plan
from ai_brooks_rag.context_builder import build_decision_messages

load_dotenv()

PERSIST_DIR = "data/vector/chroma"
COLLECTION_NAME = "brooks_chunks_v1"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dr", required=True)
    ap.add_argument("--xinfa-root", default="ai_brooks_knowledge/xinfa_core")
    args = ap.parse_args()

    with open(args.dr, "r", encoding="utf-8") as f:
        dr = json.load(f)

    plan = build_plan_from_decision_request(dr)

    db = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=PERSIST_DIR,
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"),
    )

    docs = retrieve_with_plan(db, plan)
    messages = build_decision_messages(
        decision_request=dr,
        plan=plan,
        retrieved_docs=docs,
        xinfa_root=args.xinfa_root,
    )

    print("\n=== Messages built ===")
    for i, m in enumerate(messages):
        print(f"[{i}] role={m['role']} chars={len(m['content'])}")
        print(m["content"][:])
        print("\n" + "-" * 90)

if __name__ == "__main__":
    main()
