import math
from typing import Any, Dict
from .retrieval_plan import RetrievalPlan
from .rewrite import build_template_query

def _entropy(scores: Dict[str, float]) -> float:
    # 避免 0
    vals = [max(1e-9, float(v)) for v in scores.values()]
    s = sum(vals)
    ps = [v / s for v in vals]
    return -sum(p * math.log(p) for p in ps)

def build_retrieval_plan(decision_request: Dict[str, Any]) -> RetrievalPlan:
    snap = decision_request["snapshot"]
    regime = snap["regime"]

    scores = {
        "TREND": float(regime.get("trending_score", 0.0)),
        "RANGE": float(regime.get("ranging_score", 0.0)),
        "REVERSAL": float(regime.get("reversal_setup_score", 0.0)),
        "BREAKOUT": float(regime.get("breakout_mode_score", 0.0)),
    }

    # 模糊度：熵越大越模糊
    ent = _entropy(scores)

    # 额外“冲突信号”：趋势里出现很强的反转结构
    swing = snap.get("swing", {})
    reversals = snap.get("reversals", {})
    conflict = max(
        float(swing.get("double_top_score", 0.0)),
        float(swing.get("double_bottom_score", 0.0)),
        float(reversals.get("final_flag_score", 0.0)),
        float(reversals.get("climax_runup_score", 0.0)),
    )

    query = build_template_query(decision_request)

    # v0.1：简单档位
    if ent < 0.85 and conflict < 0.65:
        # 比较明确：主书 + 少量补充
        # 选最高分对应书
        main_book = max(["TREND", "RANGE", "REVERSAL"], key=lambda b: scores[b])
        books = [main_book]
        k_per_book = {main_book: 6}
        neighbor_n = 1
        use_rerank = False
        final_k = 8
    else:
        # 模糊：多书并行 + rerank + 更深 neighbor
        # 取前两名
        ranked = sorted(["TREND", "RANGE", "REVERSAL"], key=lambda b: scores[b], reverse=True)
        books = ranked[:2]
        # 若 conflict 高，把 REVERSAL 拉进来
        if conflict >= 0.65 and "REVERSAL" not in books:
            books = [books[0], "REVERSAL"]

        k_per_book = {b: 6 for b in books}
        neighbor_n = 2
        use_rerank = True
        final_k = 14

    return RetrievalPlan(
        books=books,
        k_per_book=k_per_book,
        neighbor_n=neighbor_n,
        use_rerank=use_rerank,
        final_k=final_k,
        query=query,
        filters=None,
    )
