from typing import Any, Dict, List
from .router import build_retrieval_plan
from .rewrite import build_queries

BOOKS = {"TREND", "RANGE", "REVERSAL"}

def ensure_trade_management(plan, decision_request: Dict[str, Any]) -> None:
    """
    实盘里：只要要给 entry/SL/TP 或已经持仓，就必须检索管理规则（RANGE 第24-32章那类）。
    v0.1：直接确保 RANGE 在 books 里，并给 2 个名额。
    """
    pos = decision_request.get("position", {}) or {}
    must_manage = bool(pos.get("has_open_position"))

    # 你也可以加：如果当前要生成入场单（没有持仓但要建议下单）也应 must_manage=True
    # v0.1 先按 has_open_position 判断即可

    if must_manage:
        if "RANGE" not in plan.books:
            plan.books.append("RANGE")
        plan.k_per_book["RANGE"] = max(plan.k_per_book.get("RANGE", 0), 6)

def build_plan_from_decision_request(decision_request: Dict[str, Any]) -> Any:
    """
    返回一个 RetrievalPlan：包含 books/k/neighbor/rerank/queries/token_budget
    """
    plan = build_retrieval_plan(decision_request)

    # ✅ 生成三类 query（pattern/regime/management）
    qs = build_queries(decision_request)

    # 兼容：保留 plan.query，同时给 plan.queries
    plan.queries = qs
    plan.query = "\n".join(qs)

    ensure_trade_management(plan, decision_request)

    return plan
