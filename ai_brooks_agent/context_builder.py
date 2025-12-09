# ai_brooks_agent/context_builder.py
from ai_brooks_knowledge.xinfa_loader import (
    load_static_xinfa_core,
    load_trend_reinforcement,
    load_range_reinforcement,
    load_reversal_reinforcement,
)

from ai_brooks_features.schema import MarketSnapshot  # 假设你有这个

def build_static_xinfa(snapshot: MarketSnapshot) -> str:
    """
    返回：用于本次决策的静态 + 局部强化 xinfa 文本。
    逻辑：
      - 核心 xinfa 永远在。
      - 如果趋势 / 震荡 / 反转分数很高，额外拼一点对应模块。
    """
    core = load_static_xinfa_core()
    extra_parts = []

    reg = snapshot.regime

    # 这些阈值你后面可以自己调
    if reg.trending_score > 0.6:
        extra_parts.append(load_trend_reinforcement())

    if reg.ranging_score > 0.6:
        extra_parts.append(load_range_reinforcement())

    if reg.reversal_setup_score > 0.6:
        extra_parts.append(load_reversal_reinforcement())

    # 注意：不要把 extra_parts 拼得太长，如果觉得太多可以裁剪或只选一个最 dominant regime

    if extra_parts:
        return core + "\n\n" + "\n\n".join(extra_parts)
    else:
        return core
