from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class RetrievalPlan:
    # 哪些书、每本书取多少
    books: List[str]                 # e.g. ["TREND", "RANGE"]
    k_per_book: Dict[str, int]       # e.g. {"RANGE": 6, "TREND": 3}

    # neighbor 扩展层数
    neighbor_n: int                  # e.g. 1 or 2

    # 是否 rerank
    use_rerank: bool

    # 最终给决策模型的 chunk 数上限（去重后）
    final_k: int

    # 用于向量检索的 query（模板化 or LLM 改写后）
    query: str

    # 你可以留着以后做更细粒度过滤（v0.1 可不用）
    filters: Optional[Dict] = None
    
    queries: Optional[List[str]] = None
    token_budget: int = 6000              # 给“动态 chunks”的预算（不含 snapshot/xinfa）
    expand_from_top_m: int = 10           # 只对 top_m 做 neighbor 扩展，避免爆炸