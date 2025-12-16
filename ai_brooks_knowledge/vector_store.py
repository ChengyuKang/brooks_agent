# ai_brooks_knowledge/vector_store.py
from functools import lru_cache
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from .rag_config import BROOKS_FAISS_PATH

@lru_cache(maxsize=1)
def get_brooks_vectorstore() -> FAISS:
    """
    懒加载 + 缓存 Brooks 三本书的 FAISS 向量库。
    """
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    vs = FAISS.load_local(
        str(BROOKS_FAISS_PATH),
        embeddings,
        allow_dangerous_deserialization=True,  # 本地自己用没问题
    )
    return vs
