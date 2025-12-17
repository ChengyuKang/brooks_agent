from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()

PERSIST_DIR = "data/vector/chroma"
COLLECTION_NAME = "brooks_chunks_v1"

def main():
    db = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=PERSIST_DIR,
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"),
    )

    q = "What is a breakout pullback and how do you trade it?"
    docs = db.similarity_search(q, k=5)

    for i, d in enumerate(docs, 1):
        m = d.metadata
        print("\n" + "="*80)
        print(f"[{i}] {m.get('book')} | {m.get('chapter')} | pages {m.get('page_start')}-{m.get('page_end')}")
        print(d.page_content[:500])

if __name__ == "__main__":
    main()
