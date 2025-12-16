# ai_brooks_knowledge/rag_config.py
from pathlib import Path

# 向量库存放目录（FAISS 会生成 index + metadata）
BASE_DIR = Path(__file__).resolve().parent
VECTORSTORE_DIR = BASE_DIR / "vectorstores"
VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

BROOKS_FAISS_PATH = VECTORSTORE_DIR / "brooks_books_faiss"

# chunk 参数：字符级（LangChain 是按字符，不是 token）
CHUNK_SIZE = 1200        # 约等于 400–600 tokens
CHUNK_OVERLAP = 200      # 适当重叠，保证句子不要被硬切断

# 三本书路径（你可以改成相对路径或复制到项目里）
route_path = "C:/Users/16695/Desktop/LLM/tradeBooks/"
TREND_PDF_PATH = route_path + "trend1.pdf"
RANGE_PDF_PATH = route_path + "range2.pdf"
REVERSAL_PDF_PATH = route_path + "reversal3.pdf"
