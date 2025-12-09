# ai_brooks_knowledge/xinfa_loader.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent / "xinfa_core"

def _read(name: str) -> str:
    return (BASE_DIR / name).read_text(encoding="utf-8")

def load_static_xinfa_core() -> str:
    """
    最核心的“宪法”+ 世界观 + 风控 + 术语解释，
    每次决策都作为 system / static context 注入。
    目标体量：~1500–2500 tokens（可以先不纠结精确，后面再压缩）。
    """
    parts = [
        _read("01_core_worldview_and_risk.md"),
        _read("09_psychology_best_trades_and_routines.md"),
        _read("10_pattern_glossary_for_features.md"),
    ]
    return "\n\n".join(parts)

def load_trend_reinforcement() -> str:
    return _read("03_trend_structure_and_with_trend_setups.md")

def load_range_reinforcement() -> str:
    return _read("04_trading_ranges_magnets_and_breakout_mode.md")

def load_reversal_reinforcement() -> str:
    return _read("05_reversals_major_trend_reversals_and_final_flags.md")
