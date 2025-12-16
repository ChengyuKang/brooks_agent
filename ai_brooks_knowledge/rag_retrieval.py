# ai_brooks_knowledge/rag_retrieval.py
from __future__ import annotations

from typing import List, Tuple, Set
import textwrap

from langchain_core.documents import Document

from ai_brooks_features.schema import DecisionRequest  # 你自己的 dataclass 定义

from .vector_store import get_brooks_vectorstore


def _classify_regime(req: DecisionRequest) -> str:
    r = req.snapshot.regime
    # 简单 heuristic，可后续调参
    if r.trending_score > 0.6 and r.trending_score > r.ranging_score:
        return "trend"
    if r.ranging_score > 0.6:
        return "trading range"
    if r.reversal_setup_score > 0.5:
        return "reversal or major trend reversal"
    if r.breakout_mode_score > 0.6:
        return "breakout mode"
    return "unclear / mixed regime"


def _patterns_from_snapshot(req: DecisionRequest) -> List[str]:
    s = req.snapshot
    pat = []

    if s.swing.double_top_score > 0.5:
        pat.append("double top")
    if s.swing.double_bottom_score > 0.5:
        pat.append("double bottom")
    if s.swing.wedge_score > 0.5 or s.swing.wedge_push_count >= 3:
        pat.append("wedge pattern")
    if s.reversals.climax_runup_score > 0.5:
        pat.append("buy/sell climax")
    if s.reversals.final_flag_score > 0.5:
        pat.append("final flag")
    if s.reversals.high2_score > 0.5:
        pat.append("High 2 setup")
    if s.reversals.low2_score > 0.5:
        pat.append("Low 2 setup")

    if not pat:
        pat.append("general price action context")

    return pat


def _time_of_day_bucket(req: DecisionRequest) -> str:
    t = req.snapshot.time_of_day_fraction
    if t < 0.3:
        return "opening session"
    if t < 0.7:
        return "midday session"
    return "late session near the close"


def _build_queries(req: DecisionRequest) -> List[str]:
    regime = _classify_regime(req)
    patterns = _patterns_from_snapshot(req)
    tod = _time_of_day_bucket(req)

    # 基础 world 状态
    base = (
        f"Brooks intraday trading rules for {regime} conditions on ES/SPY 5-minute chart "
        f"during the {tod}. Focus on how to trade, when not to trade, and risk management."
    )

    queries = [base]

    # pattern 细化
    for pat in patterns:
        q = (
            f"How does Brooks trade {pat} in {regime} conditions on intraday ES/SPY, "
            f"including entry, stop placement, targets, and when the pattern is unreliable?"
        )
        queries.append(q)

    # 额外：range vs trend 冲突时的防踩坑建议
    queries.append(
        "Warnings from Brooks about trading in choppy markets, barbwire, or when the trend "
        "and trading range evidence are mixed, especially when traders should stand aside."
    )

    return queries


def _similarity_search_multi(queries: List[str], k_per_query: int = 4) -> List[Document]:
    vs = get_brooks_vectorstore()
    results: List[Document] = []
    seen_ids: Set[Tuple[str, int, str]] = set()

    for q in queries:
        docs = vs.similarity_search(q, k=k_per_query)
        for d in docs:
            # 用 (book, page, snippet hash) 去重
            key = (
                d.metadata.get("book", ""),
                d.metadata.get("page", -1),
                d.metadata.get("source", ""),
            )
            if key in seen_ids:
                continue
            seen_ids.add(key)
            results.append(d)

    return results


def _is_complex_situation(req: DecisionRequest) -> bool:
    r = req.snapshot.regime
    s = req.snapshot.swing
    rev = req.snapshot.reversals

    # 趋势 & 震荡都不低，且有明显反转结构 → 复杂
    mixed_regime = r.trending_score > 0.4 and r.ranging_score > 0.4
    strong_reversal = (
        r.reversal_setup_score > 0.4
        or s.wedge_score > 0.4
        or s.double_top_score > 0.4
        or s.double_bottom_score > 0.4
        or rev.climax_runup_score > 0.5
    )
    return mixed_regime or strong_reversal


def build_brooks_context_summary(req: DecisionRequest, *, debug: bool = False) -> str:
    """
    构建「针对当前 DecisionRequest 的 Brooks 书本上下文总结」。
    这段文本会在决策 prompt 里出现在 xinfa 后面。

    逻辑：
      1. 用 snapshot 衍生出多视角 query（regime + pattern + warning）。
      2. 从 FAISS 检索多组 chunk，去重。
      3. 根据简单/复杂情形，控制 raw chunk 数量。
      4. 调用 LLM 把 raw chunk 总结成 800–1200 tokens 左右的一段说明文字。
    """
    queries = _build_queries(req)

    # 简单 vs 复杂：控制检索量
    if _is_complex_situation(req):
        k_per_query = 5   # 复杂场景多拿一点
    else:
        k_per_query = 3   # 简单场景少一点，避免信息过载

    raw_docs = _similarity_search_multi(queries, k_per_query=k_per_query)

    if debug:
        print(f"[RAG] queries ({len(queries)}):")
        for q in queries:
            print("  -", q)
        print(f"[RAG] retrieved raw_docs: {len(raw_docs)}")
        for d in raw_docs[:5]:
            print("  ->", d.metadata)

    # 把 raw_docs 合并成一个大文本，供 summarizer 使用
    joined_chunks = "\n\n---\n\n".join(
        f"[{d.metadata.get('book', 'unknown')} p.{d.metadata.get('page', '?')}]\n{d.page_content}"
        for d in raw_docs
    )

    # ❗ 这里需要你自己实现一个 LLM 调用，比如 call_gpt_5_1
    from ai_brooks_agent.llm_client import call_gpt_5_1  # 你自己写的 client 封装

    system_prompt = textwrap.dedent("""
        You are summarizing Al Brooks' three books on price action trading.
        Your goal is to create a concise but rich context document that is
        specifically useful for the CURRENT situation, not a general summary.

        - Focus on the most relevant rules, principles, warnings, and trade ideas
          for the described regime, patterns, and time of day.
        - Emphasize:
          * when to trade vs when NOT to trade,
          * with-trend entries vs countertrend vs range fades,
          * risk management and trader's equation,
          * typical mistakes and traps in this context.
        - Ignore long stories and examples unless they clearly illustrate a rule.
        - DO NOT quote long passages verbatim; paraphrase instead.
        - If the environment is unclear / mixed, explicitly say so and lean toward caution.
    """)

    # 用 DecisionRequest 做一个简短 summary，让 summarizer知道当前发生了什么
    snapshot = req.snapshot
    regime_label = _classify_regime(req)
    patterns = ", ".join(_patterns_from_snapshot(req))
    tod = _time_of_day_bucket(req)

    user_prompt = textwrap.dedent(f"""
        Here is a description of the current market situation:

        - Instrument: {snapshot.meta.symbol}
        - Timeframe: {snapshot.timeframe_minutes} minutes
        - Approx time of day: {tod}
        - Classified regime: {regime_label}
        - Notable patterns / scores: {patterns}
        - Regime scores: trending={snapshot.regime.trending_score:.2f}, 
                         ranging={snapshot.regime.ranging_score:.2f}, 
                         reversal_setup={snapshot.regime.reversal_setup_score:.2f}, 
                         breakout_mode={snapshot.regime.breakout_mode_score:.2f}

        Now here are multiple chunks extracted from Al Brooks' books,
        which may or may not be all relevant:

        ---------------- CHUNKS START ----------------
        {joined_chunks}
        ----------------- CHUNKS END -----------------

        Please produce a SINGLE coherent summary (around 800–1200 tokens) that
        captures the most relevant Brooks guidance for this specific situation.
        Structure your answer as:

        1. Regime interpretation (how Brooks would likely label this environment)
        2. Valid trade types (with-trend, countertrend, fade range, breakout) and which are preferred
        3. Entry ideas and signal quality considerations
        4. Stop and target logic appropriate here
        5. Situations where Brooks would advise to stand aside
        6. Any special warnings or traps mentioned in the chunks that apply here
    """)

    summary = call_gpt_5_1(system_prompt=system_prompt, user_prompt=user_prompt)
    return summary
