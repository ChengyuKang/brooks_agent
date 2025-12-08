# ai_brooks_features/feature_calculators.py
from __future__ import annotations

from typing import Optional, Literal

import numpy as np
import pandas as pd

from .schema import (
    BarStats,
    LocalTrendStats,
    RangeStructure,
    SwingStructure,
    ReversalSignals,
    RiskRewardMetrics,
    RegimeScores,
)
from .config import ATR_PERIOD, TREND_LOOKBACK, RANGE_LOOKBACK, EMA_PERIOD
from .indicators import ema, atr, volume_zscore


# ---------- BarStats ----------

def compute_bar_stats(df: pd.DataFrame, i: int, atr_series: pd.Series) -> BarStats:
    row = df.iloc[i]
    prev_row = df.iloc[i - 1] if i > 0 else row
    atr_val = float(atr_series.iloc[i]) if not np.isnan(atr_series.iloc[i]) else 0.0

    high = row["high"]
    low = row["low"]
    op = row["open"]
    close = row["close"]
    rng = max(high - low, 1e-9)

    body = abs(close - op)
    upper_tail = max(high - max(op, close), 0.0)
    lower_tail = max(min(op, close) - low, 0.0)

    body_rel = body / rng
    upper_tail_rel = upper_tail / rng
    lower_tail_rel = lower_tail / rng
    close_pos_rel = (close - low) / rng

    range_rel_atr = (rng / atr_val) if atr_val > 0 else 0.0

    # gap 相对 ATR
    gap_to_prev_close = 0.0
    if atr_val > 0:
        gap_to_prev_close = (op - prev_row["close"]) / atr_val

    # 简单趋势 bar score：实体大 + close 靠近极端 + 影线短
    trend_body = min(body_rel / 0.7, 1.0)          # >0.7 视为大实体
    trend_close_to_edge = max(1.0 - abs(close_pos_rel - 0.5) * 2.0, 0.0)
    tail_penalty = max(0.0, 1.0 - (upper_tail_rel + lower_tail_rel))
    is_trend_bar_score = float(
        max(0.0, min((trend_body * 0.5 + trend_close_to_edge * 0.3 + tail_penalty * 0.2), 1.0))
    )

    # doji score：实体越小越接近 1
    is_doji_score = float(min((0.4 - body_rel) / 0.4, 1.0)) if body_rel < 0.4 else 0.0
    is_doji_score = max(is_doji_score, 0.0)

    # inside / outside 简单判断
    prev_high = prev_row["high"]
    prev_low = prev_row["low"]
    is_outside = high > prev_high and low < prev_low
    is_inside = high < prev_high and low > prev_low

    is_outside_score = 1.0 if is_outside else 0.0
    is_inside_score = 1.0 if is_inside else 0.0

    return BarStats(
        body_rel=body_rel,
        upper_tail_rel=upper_tail_rel,
        lower_tail_rel=lower_tail_rel,
        close_pos_rel=close_pos_rel,
        range_rel_atr=range_rel_atr,
        gap_to_prev_close=gap_to_prev_close,
        is_trend_bar_score=is_trend_bar_score,
        is_doji_score=is_doji_score,
        is_outside_score=is_outside_score,
        is_inside_score=is_inside_score,
        volume_zscore=float(row.get("volume_zscore", 0.0)),
    )


# ---------- LocalTrendStats ----------

def compute_local_trend_stats(
    df: pd.DataFrame,
    i: int,
    ema_series: pd.Series,
    atr_series: pd.Series,
    lookback: int = TREND_LOOKBACK,
) -> LocalTrendStats:
    atr_val = float(atr_series.iloc[i]) if not np.isnan(atr_series.iloc[i]) else 0.0

    # ema_slope: (ema[i] - ema[i-k]) / (ATR * k)
    k = min(lookback, i) if i > 0 else 1
    ema_now = float(ema_series.iloc[i])
    ema_past = float(ema_series.iloc[i - k])
    ema_slope = 0.0
    if atr_val > 0 and k > 0:
        ema_slope = (ema_now - ema_past) / (atr_val * k)

    # bars_above_ema_ratio
    start_idx = max(0, i - lookback + 1)
    window = df.iloc[start_idx : i + 1]
    ema_win = ema_series.iloc[start_idx : i + 1]
    bars_above = (window["close"] > ema_win).sum()
    total_bars = len(window)
    bars_above_ema_ratio = float(bars_above) / total_bars if total_bars > 0 else 0.0

    # 连续阳线 / 阴线
    consecutive_bull = 0
    consecutive_bear = 0
    for j in range(i, max(i - lookback, -1), -1):
        row = df.iloc[j]
        if row["close"] > row["open"]:
            if consecutive_bear > 0:
                break
            consecutive_bull += 1
        elif row["close"] < row["open"]:
            if consecutive_bull > 0:
                break
            consecutive_bear += 1
        else:
            break

    # 微通道：简单版 - 连续 bar low 抬高 或 high 降低
    micro_channel_bars = 0
    direction: Optional[Literal["up", "down"]] = None
    prev_low = df.iloc[i]["low"]
    prev_high = df.iloc[i]["high"]
    for j in range(i - 1, max(i - lookback, -1), -1):
        row = df.iloc[j]
        if direction is None:
            if row["low"] < prev_low:
                direction = "up"
            elif row["high"] > prev_high:
                direction = "down"
            else:
                break
        if direction == "up":
            if row["low"] < prev_low:
                micro_channel_bars += 1
                prev_low = row["low"]
            else:
                break
        elif direction == "down":
            if row["high"] > prev_high:
                micro_channel_bars += 1
                prev_high = row["high"]
            else:
                break

    # 暂时不做精细 pullback / spike，后面迭代
    pullback_depth_rel = 0.0   # TODO
    pullback_bars = 0          # TODO
    spike_strength = 0.0       # TODO
    trend_persistence = float(
        np.clip(
            0.5 * abs(ema_slope) + 0.3 * bars_above_ema_ratio + 0.2 * (micro_channel_bars / max(lookback, 1)),
            0.0,
            1.0,
        )
    )

    return LocalTrendStats(
        ema_slope=float(ema_slope),
        bars_above_ema_ratio=float(bars_above_ema_ratio),
        consecutive_bull_bars=int(consecutive_bull),
        consecutive_bear_bars=int(consecutive_bear),
        micro_channel_bars=int(micro_channel_bars),
        pullback_depth_rel=float(pullback_depth_rel),
        pullback_bars=int(pullback_bars),
        spike_strength=float(spike_strength),
        trend_persistence=float(trend_persistence),
    )


# ---------- RangeStructure ----------

def compute_range_structure(
    df: pd.DataFrame,
    i: int,
    atr_series: pd.Series,
    lookback: int = RANGE_LOOKBACK,
) -> RangeStructure:
    """
    MVP 版本：实现 overlap_ratio & range_height_rel_atr，
    其他字段留 TODO。
    """
    start_idx = max(0, i - lookback + 1)
    window = df.iloc[start_idx : i + 1]
    atr_val = float(atr_series.iloc[i]) if not np.isnan(atr_series.iloc[i]) else 0.0

    # overlap_ratio：统计有多少 bar 与前一根高低区间有重叠
    overlaps = 0
    for j in range(start_idx + 1, i + 1):
        prev = df.iloc[j - 1]
        cur = df.iloc[j]
        if cur["low"] <= prev["high"] and cur["high"] >= prev["low"]:
            overlaps += 1
    total_pairs = max(1, (i + 1) - start_idx - 1)
    overlap_ratio = overlaps / total_pairs

    # range_height_rel_atr：窗口内最高价-最低价 / ATR
    if len(window) > 0 and atr_val > 0:
        hi = float(window["high"].max())
        lo = float(window["low"].min())
        range_height_rel_atr = (hi - lo) / atr_val
    else:
        range_height_rel_atr = 0.0

    # 其他占位
    time_in_range_bars = 0
    tests_of_range_high = 0
    tests_of_range_low = 0
    breakout_attempts = 0
    breakout_fail_ratio = 0.0
    barbwire_score = 0.0

    return RangeStructure(
        overlap_ratio=float(overlap_ratio),
        range_height_rel_atr=float(range_height_rel_atr),
        time_in_range_bars=int(time_in_range_bars),
        tests_of_range_high=int(tests_of_range_high),
        tests_of_range_low=int(tests_of_range_low),
        breakout_attempts=int(breakout_attempts),
        breakout_fail_ratio=float(breakout_fail_ratio),
        barbwire_score=float(barbwire_score),
    )


# ---------- 空占位结构（后面慢慢填） ----------

def empty_swing_structure() -> SwingStructure:
    return SwingStructure(
        swing_direction=0.0,
        hh_ll_score=0.0,
        swing_leg1_size=0.0,
        swing_leg2_size=0.0,
        leg2_vs_leg1_ratio=0.0,
        wedge_push_count=0,
        wedge_score=0.0,
        double_top_score=0.0,
        double_bottom_score=0.0,
    )


def empty_reversal_signals() -> ReversalSignals:
    return ReversalSignals(
        trendline_break_score=0.0,
        channel_overshoot_score=0.0,
        climax_runup_score=0.0,
        pullback_after_climax_bars=0,
        higher_low_score=0.0,
        lower_high_score=0.0,
        high1_score=0.0,
        high2_score=0.0,
        low1_score=0.0,
        low2_score=0.0,
        final_flag_score=0.0,
    )


def empty_risk_reward() -> RiskRewardMetrics:
    return RiskRewardMetrics(
        nearest_support_dist=0.0,
        nearest_resistance_dist=0.0,
        stop_distance_suggested=0.0,
        scalp_target_dist=0.0,
        swing_target_dist=0.0,
        rr_swing_estimate=0.0,
        rr_scalp_estimate=0.0,
        prob_trend_continuation=0.0,
        prob_reversal=0.0,
        prob_range_continuation=0.0,
    )


# ---------- RegimeScores ----------

def compute_regime_scores(
    local_trend: LocalTrendStats,
    trading_range: RangeStructure,
) -> RegimeScores:
    """
    MVP: 用简单 heuristic 给趋势/震荡打分。
    """
    # 趋势分：EMA 斜率 + micro_channel + bars_above_ema_ratio
    trend_strength = (
        0.4 * min(abs(local_trend.ema_slope) * 5.0, 1.0)
        + 0.3 * local_trend.bars_above_ema_ratio
        + 0.3 * min(local_trend.micro_channel_bars / 10.0, 1.0)
    )
    trend_strength = float(np.clip(trend_strength, 0.0, 1.0))

    # 区间分：overlap_ratio + range_height_rel_atr 接近 1~2
    range_overlap = trading_range.overlap_ratio
    h = trading_range.range_height_rel_atr
    if h <= 0:
        height_score = 0.0
    elif h < 0.5:
        height_score = h / 0.5
    elif h <= 2.0:
        height_score = 1.0
    else:
        height_score = max(0.0, 1.0 - (h - 2.0) / 3.0)
    range_score = float(np.clip(0.6 * range_overlap + 0.4 * height_score, 0.0, 1.0))

    reversal_setup_score = 0.0  # TODO: 以后结合 ReversalSignals
    breakout_mode_score = 0.0   # TODO

    return RegimeScores(
        trending_score=trend_strength,
        ranging_score=range_score,
        reversal_setup_score=reversal_setup_score,
        breakout_mode_score=breakout_mode_score,
    )


# ---------- 批量预处理辅助 ----------

def precompute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    给 builder 用：在原 df 上加好 ATR / EMA / volume_zscore 等列。
    """
    df = df.copy()
    df["atr"] = atr(df, period=ATR_PERIOD)
    df["ema"] = ema(df["close"], period=EMA_PERIOD)
    df["volume_zscore"] = volume_zscore(df["volume"])
    return df
