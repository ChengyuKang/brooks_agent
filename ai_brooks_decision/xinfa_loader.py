from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

@dataclass
class XinfaDoc:
    doc_id: str           # e.g. XINFA:01_core_worldview_and_risk.md
    path: str
    text: str
    approx_tokens: int

def approx_tokens(text: str) -> int:
    # 粗略估算：英文大约 4 chars/token；markdown 有符号略保守
    return max(1, len(text) // 4)

def load_xinfa_docs(root_dir: str) -> Dict[str, XinfaDoc]:
    """
    root_dir: brooks_agent/ai_brooks_knowledge/xinfa_core
    return: filename -> XinfaDoc
    """
    out: Dict[str, XinfaDoc] = {}
    for name in sorted(os.listdir(root_dir)):
        if not name.lower().endswith(".md"):
            continue
        p = os.path.join(root_dir, name)
        with open(p, "r", encoding="utf-8") as f:
            text = f.read().strip()
        out[name] = XinfaDoc(
            doc_id=f"XINFA:{name}",
            path=p,
            text=text,
            approx_tokens=approx_tokens(text),
        )
    return out

def pick_xinfa_set(
    all_docs: Dict[str, XinfaDoc],
    plan_books: List[str],
    system_budget: int = 2500,
    static_budget: int = 3000,
) -> Tuple[List[XinfaDoc], List[XinfaDoc]]:
    """
    返回 (system_docs, static_docs)，均会按预算裁剪（按优先级取全文，不做摘要）
    """
    # 你的模块映射
    A = "01_core_worldview_and_risk.md"
    E = "09_psychology_best_trades_and_routines.md"
    F = "10_pattern_glossary_for_features.md"

    COMMON = [
        "02_bar_language_and_micro_patterns.md",
        "06_multitimeframe_and_regime_transitions.md",
        "07_intraday_structure_open_midday_close.md",
        "08_order_entry_trade_management_and_scaling.md",
    ]

    REGIME_MAP = {
        "TREND": "03_trend_structure_and_with_trend_setups.md",
        "RANGE": "04_trading_ranges_magnets_and_breakout_mode.md",
        "REVERSAL": "05_reversals_major_trend_reversals_and_final_flags.md",
    }

    # 1) system 固定
    sys_names = [A, E, F]
    system_docs: List[XinfaDoc] = [all_docs[n] for n in sys_names if n in all_docs]

    # 2) static：通用 + regime
    static_names = []
    static_names.extend([n for n in COMMON if n in all_docs])

    # 按 plan_books 选 regime 文件（去重）
    for b in plan_books:
        b = (b or "").upper()
        if b in REGIME_MAP and REGIME_MAP[b] in all_docs:
            static_names.append(REGIME_MAP[b])

    # 去重保持顺序
    seen = set()
    static_names = [x for x in static_names if not (x in seen or seen.add(x))]
    static_docs: List[XinfaDoc] = [all_docs[n] for n in static_names]

    # 按预算裁剪（简单：按顺序取全文直到超预算；不摘要）
    def apply_budget(docs: List[XinfaDoc], budget: int) -> List[XinfaDoc]:
        used = 0
        out = []
        for d in docs:
            if used + d.approx_tokens > budget:
                continue
            out.append(d)
            used += d.approx_tokens
        return out

    return apply_budget(system_docs, system_budget), apply_budget(static_docs, static_budget)
