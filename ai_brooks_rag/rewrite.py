from typing import Any, Dict, List

def _top_flags(decision_request: Dict[str, Any]) -> List[str]:
    snap = decision_request["snapshot"]
    bar = snap.get("bar", {})
    local = snap.get("local_trend", {})
    swing = snap.get("swing", {})
    tr = snap.get("trading_range", {})
    rev = snap.get("reversals", {})
    regime = snap.get("regime", {})

    flags = []

    # pattern/structure
    if float(swing.get("double_top_score", 0)) > 0.65:
        flags.append("double top bear flag")
    if float(swing.get("double_bottom_score", 0)) > 0.65:
        flags.append("double bottom bull flag")
    if float(swing.get("wedge_score", 0)) > 0.55:
        flags.append("wedge / three pushes")
    if int(local.get("micro_channel_bars", 0)) >= 3:
        flags.append("micro channel")
    if float(rev.get("final_flag_score", 0)) > 0.55:
        flags.append("final flag")
    if float(rev.get("climax_runup_score", 0)) > 0.45:
        flags.append("climactic move / climax")
    if float(tr.get("breakout_fail_ratio", 0)) > 0.5:
        flags.append("failed breakout")
    if float(tr.get("barbwire_score", 0)) > 0.5:
        flags.append("barbwire / tight trading range")

    # signal bars / bar counting (低成本关键词，提升召回)
    if float(rev.get("high2_score", 0)) > 0.4:
        flags.append("High 2")
    if float(rev.get("high1_score", 0)) > 0.4:
        flags.append("High 1")
    if float(rev.get("low2_score", 0)) > 0.4:
        flags.append("Low 2")
    if float(rev.get("low1_score", 0)) > 0.4:
        flags.append("Low 1")

    # regime hints
    if float(regime.get("breakout_mode_score", 0)) > 0.5:
        flags.append("breakout mode")

    return flags[:8]

def build_queries(decision_request: Dict[str, Any]) -> List[str]:
    snap = decision_request["snapshot"]
    regime = snap.get("regime", {})
    pos = decision_request.get("position", {}) or {}

    flags = _top_flags(decision_request)

    regime_q = (
        f"price action regime decision: trend vs trading range vs reversal; "
        f"always in; overlap ambiguity; "
        f"trending_score={regime.get('trending_score',0):.2f}, "
        f"ranging_score={regime.get('ranging_score',0):.2f}, "
        f"reversal_setup_score={regime.get('reversal_setup_score',0):.2f}, "
        f"breakout_mode_score={regime.get('breakout_mode_score',0):.2f}"
    )

    pattern_q = " ".join([
        "setup and entry tactics:", *flags,
        "second entry", "breakout pullback", "measured move", "signal bar", "stop entry"
    ])

    if bool(pos.get("has_open_position")):
        mgmt_q = "MGMT|trade management: protective stop, trailing stop, scaling in/out, profit targets, trader's equation"
    else:
        mgmt_q = "MGMT|trade decision checklist: need two reasons, probability vs risk reward, protective stop placement, profit targets"
    
    # v0.1 返回三条：检索时分别查，再合并去重（比拼成一条更稳）
    return [pattern_q, regime_q, mgmt_q]

def build_template_query(decision_request: Dict[str, Any]) -> str:
    snap = decision_request["snapshot"]
    bar = snap["bar"]
    local = snap["local_trend"]
    swing = snap["swing"]
    tr = snap["trading_range"]
    rev = snap["reversals"]
    rr = snap["risk_reward"]

    parts = []

    # 市场类型
    regime = snap["regime"]
    parts.append(
        f"Regime: trending={regime.get('trending_score',0):.2f}, "
        f"ranging={regime.get('ranging_score',0):.2f}, "
        f"reversal_setup={regime.get('reversal_setup_score',0):.2f}, "
        f"breakout_mode={regime.get('breakout_mode_score',0):.2f}"
    )

    # bar 形态（Brooks 术语相关）
    parts.append(
        f"Bar: trend_bar_score={bar.get('is_trend_bar_score',0):.2f}, "
        f"doji={bar.get('is_doji_score',0):.2f}, "
        f"range_ATR={bar.get('range_rel_atr',0):.2f}, "
        f"close_pos={bar.get('close_pos_rel',0):.2f}, "
        f"upper_tail={bar.get('upper_tail_rel',0):.2f}, "
        f"lower_tail={bar.get('lower_tail_rel',0):.2f}"
    )

    # 结构：double top/bottom, wedge, micro channel
    parts.append(
        f"Structure: double_top={swing.get('double_top_score',0):.2f}, "
        f"double_bottom={swing.get('double_bottom_score',0):.2f}, "
        f"wedge={swing.get('wedge_score',0):.2f}, "
        f"micro_channel_bars={local.get('micro_channel_bars',0)}"
    )

    # trading range 特征
    parts.append(
        f"TradingRange: overlap={tr.get('overlap_ratio',0):.2f}, "
        f"tests_high={tr.get('tests_of_range_high',0)}, "
        f"tests_low={tr.get('tests_of_range_low',0)}, "
        f"breakout_fail_ratio={tr.get('breakout_fail_ratio',0):.2f}"
    )

    # reversal 类信号
    parts.append(
        f"ReversalSignals: climax={rev.get('climax_runup_score',0):.2f}, "
        f"final_flag={rev.get('final_flag_score',0):.2f}, "
        f"high1={rev.get('high1_score',0):.2f}, high2={rev.get('high2_score',0):.2f}, "
        f"low1={rev.get('low1_score',0):.2f}, low2={rev.get('low2_score',0):.2f}"
    )

    # 交易管理（让它去找 trader's equation / need two reasons / stops / targets）
    parts.append(
        f"RiskReward: rr_swing={rr.get('rr_swing_estimate',0):.2f}, "
        f"rr_scalp={rr.get('rr_scalp_estimate',0):.2f}, "
        f"stop_suggested_ATR={rr.get('stop_distance_suggested',0):.2f}"
    )

    return "\n".join(parts)
