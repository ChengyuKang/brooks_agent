# ai_brooks_features/feature_calculators.py
from __future__ import annotations

from typing import Optional, Literal, List, Tuple

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

    # ====== 新增：pullback 粗略检测 ======
    # 思路：找最近 N 根里离 EMA 最远的方向作为“主腿”，当前 close 相对那一点的回撤深度
    pullback_depth_rel = 0.0
    pullback_bars = 0
    if atr_val > 0 and total_bars > 5:
        # 窗口内找离 EMA 最远的 bar
        distances = (window["close"] - ema_win).abs()
        max_idx_in_win = distances.idxmax()
        max_pos = window.index.get_loc(max_idx_in_win)
        # 主腿方向：close - ema 的符号
        main_dir = np.sign((window.loc[max_idx_in_win, "close"] - ema_win[max_idx_in_win]))
        # 如果当前和主腿同向，则 pullback 很浅
        # 如果反向，则以那一点为 extremum 计算回撤
        if main_dir != 0:
            leg_extreme_price = window.loc[max_idx_in_win, "close"]
            curr_price = window.iloc[-1]["close"]
            leg_size = abs(leg_extreme_price - ema_win[max_idx_in_win])
            pullback = abs(curr_price - leg_extreme_price)
            if leg_size > 0:
                pullback_depth_rel = min(pullback / (leg_size + 1e-9), 3.0)
            # 粗略估算 pullback_bars：从 extremum 到现在的 bar 数
            pullback_bars = (window.shape[0] - 1) - max_pos

    # spike_strength 暂时用 ema_slope + micro_channel 近似
    spike_strength = float(
        np.clip(
            abs(ema_slope) * 3.0 + micro_channel_bars / max(lookback, 1),
            0.0,
            1.0,
        )
    )

    trend_persistence = float(
        np.clip(
            0.5 * abs(ema_slope) * 3.0 + 0.3 * bars_above_ema_ratio + 0.2 * (micro_channel_bars / max(lookback, 1)),
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


# ---------- Swing 检测辅助 ----------

def detect_swings_window(
    df: pd.DataFrame,
    start_idx: int,
    end_idx: int,
    pivot_span: int = 2,
    min_price_move_atr: float = 0.3,
    atr_series: Optional[pd.Series] = None,
) -> List[Tuple[int, str, float]]:
    """
    检测 [start_idx, end_idx] 区间内的 swing 高低点。
    返回列表: [(idx, "H"/"L", price), ...] 按 idx 排序。
    pivot_span: 左右各多少根作局部极值
    min_price_move_atr: 相邻 swing 之间至少多少 ATR 才算有效
    """
    swings: List[Tuple[int, str, float]] = []
    n = len(df)
    if end_idx - start_idx < 2 * pivot_span + 1:
        return swings

    for j in range(start_idx + pivot_span, end_idx - pivot_span + 1):
        segment = df.iloc[j - pivot_span : j + pivot_span + 1]
        h = df.iloc[j]["high"]
        l = df.iloc[j]["low"]
        if h == segment["high"].max():
            swings.append((j, "H", h))
        elif l == segment["low"].min():
            swings.append((j, "L", l))

    # 去掉太近/太小的 swing
    filtered: List[Tuple[int, str, float]] = []
    prev_idx = None
    prev_price = None
    for idx, typ, price in swings:
        if prev_idx is None:
            filtered.append((idx, typ, price))
            prev_idx = idx
            prev_price = price
        else:
            # 至少隔一根 bar
            if idx <= prev_idx:
                continue
            # 价格变动至少 min_price_move_atr * ATR
            if atr_series is not None:
                atr_val = float(atr_series.iloc[idx])
                if atr_val > 0:
                    if abs(price - prev_price) < min_price_move_atr * atr_val:
                        # 太近的 swing，跳过
                        continue
            filtered.append((idx, typ, price))
            prev_idx = idx
            prev_price = price

    return filtered


def compute_swing_structure(
    df: pd.DataFrame,
    i: int,
    atr_series: pd.Series,
    lookback_bars: int = 60,
) -> SwingStructure:
    """
    基于最近 ~60 根 bar 做 swing 分析，填充 SwingStructure。
    """
    end_idx = i
    start_idx = max(0, i - lookback_bars)
    swings = detect_swings_window(df, start_idx, end_idx, pivot_span=2, min_price_move_atr=0.3, atr_series=atr_series)

    if len(swings) < 3:
        # 不足以构成两条腿
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

    # 取最近的 3~4 个 swing 点
    swings_sorted = sorted(swings, key=lambda x: x[0])
    recent = swings_sorted[-4:]  # 至多 4 个

    # 最近两个 leg：[(idx, type, price)...]
    # leg1: recent[-3] -> recent[-2]
    # leg2: recent[-2] -> recent[-1]
    if len(recent) >= 3:
        idx_a, typ_a, price_a = recent[-3]
        idx_b, typ_b, price_b = recent[-2]
        idx_c, typ_c, price_c = recent[-1]

        atr_now = float(atr_series.iloc[i]) if not np.isnan(atr_series.iloc[i]) else 0.0
        swing_leg1_size = 0.0
        swing_leg2_size = 0.0
        leg2_vs_leg1_ratio = 0.0
        swing_direction = 0.0

        if atr_now > 0:
            swing_leg1_size = abs(price_b - price_a) / atr_now
            swing_leg2_size = abs(price_c - price_b) / atr_now
            if swing_leg1_size > 0:
                leg2_vs_leg1_ratio = swing_leg2_size / swing_leg1_size

        # 最近一条腿方向
        if price_c > price_b:
            swing_direction = 1.0
        elif price_c < price_b:
            swing_direction = -1.0
        else:
            swing_direction = 0.0
    else:
        swing_leg1_size = 0.0
        swing_leg2_size = 0.0
        leg2_vs_leg1_ratio = 0.0
        swing_direction = 0.0
        idx_a = idx_b = idx_c = 0
        typ_a = typ_b = typ_c = "H"
        price_a = price_b = price_c = 0.0

    # hh_ll_score：最近若干 swing 是否明显 HH/HL 或 LL/LH
    hh_ll_score = 0.0
    if len(swings_sorted) >= 4:
        last4 = swings_sorted[-4:]
        prices = [p for (_, _, p) in last4]
        highs = [p for (_, t, p) in last4 if t == "H"]
        lows = [p for (_, t, p) in last4 if t == "L"]
        score = 0.0
        if len(highs) >= 2:
            # 高点是否抬高
            if highs[-1] > highs[-2]:
                score += 0.5
        if len(lows) >= 2:
            # 低点是否抬高
            if lows[-1] > lows[-2]:
                score += 0.5
        hh_ll_score = score

    # wedge_push_count & wedge_score：最近同向推动次数
    wedge_push_count = 0
    wedge_score = 0.0
    if len(swings_sorted) >= 5:
        # 看最近 5 个 swing 的价格序列
        last5 = swings_sorted[-5:]
        dirs = []
        for (i1, _t1, p1), (i2, _t2, p2) in zip(last5[:-1], last5[1:]):
            if p2 > p1:
                dirs.append(1)
            elif p2 < p1:
                dirs.append(-1)
            else:
                dirs.append(0)
        # 看最近连续相同方向的推送次数
        cur_dir = dirs[-1]
        if cur_dir != 0:
            count = 1
            for d in reversed(dirs[:-1]):
                if d == cur_dir:
                    count += 1
                else:
                    break
            wedge_push_count = count
            if count >= 3:
                wedge_score = 1.0
            elif count == 2:
                wedge_score = 0.5

    # double top/bottom score：最近两个 swing 高点/低点价格接近
    double_top_score = 0.0
    double_bottom_score = 0.0
    atr_now = float(atr_series.iloc[i]) if not np.isnan(atr_series.iloc[i]) else 0.0
    if atr_now > 0 and len(swings_sorted) >= 4:
        highs = [p for (_, t, p) in swings_sorted if t == "H"]
        lows = [p for (_, t, p) in swings_sorted if t == "L"]
        if len(highs) >= 2:
            h1, h2 = highs[-2], highs[-1]
            diff = abs(h2 - h1) / atr_now
            if diff < 0.5:
                double_top_score = max(0.0, 1.0 - diff / 0.5)  # diff 越小分越高
        if len(lows) >= 2:
            l1, l2 = lows[-2], lows[-1]
            diff = abs(l2 - l1) / atr_now
            if diff < 0.5:
                double_bottom_score = max(0.0, 1.0 - diff / 0.5)

    return SwingStructure(
        swing_direction=float(swing_direction),
        hh_ll_score=float(hh_ll_score),
        swing_leg1_size=float(swing_leg1_size),
        swing_leg2_size=float(swing_leg2_size),
        leg2_vs_leg1_ratio=float(leg2_vs_leg1_ratio),
        wedge_push_count=int(wedge_push_count),
        wedge_score=float(wedge_score),
        double_top_score=float(double_top_score),
        double_bottom_score=float(double_bottom_score),
    )


# ---------- RangeStructure ----------

def compute_range_structure(
    df: pd.DataFrame,
    i: int,
    atr_series: pd.Series,
    lookback: int = RANGE_LOOKBACK,
) -> RangeStructure:
    """
    MVP+：在 overlap_ratio & range_height_rel_atr 的基础上，补充：
    - time_in_range_bars（很粗略）
    - tests_of_range_high / low
    - breakout_attempts / breakout_fail_ratio
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
        hi = lo = 0.0

    # ====== 新增：区间边界测试 & 假突破 ======
    tests_of_range_high = 0
    tests_of_range_low = 0
    breakout_attempts = 0
    breakout_fail_ratio = 0.0

    if len(window) > 0 and range_height_rel_atr > 0:
        # 定义区间上下沿
        range_high = hi
        range_low = lo
        # 容差：0.2 ATR
        tol = 0.2 * atr_val if atr_val > 0 else (hi - lo) * 0.05

        # 遍历窗口 bar，看是否触碰区间边界
        hits_high = 0
        hits_low = 0
        attempts = 0
        fail_count = 0

        prices = window["close"].values
        highs = window["high"].values
        lows = window["low"].values

        for k in range(len(window)):
            h = highs[k]
            l = lows[k]
            c = prices[k]
            # 触及区间上沿附近视为 test
            if abs(h - range_high) <= tol:
                hits_high += 1
            # 触及区间下沿附近视为 test
            if abs(l - range_low) <= tol:
                hits_low += 1

            # 突破尝试：bar 超过 range_high 或跌破 range_low
            if h > range_high + tol:
                attempts += 1
                # 简单判定“失败”：后一个收盘又落回区间
                if k + 1 < len(window):
                    c_next = prices[k + 1]
                    if range_low - tol <= c_next <= range_high + tol:
                        fail_count += 1
            elif l < range_low - tol:
                attempts += 1
                if k + 1 < len(window):
                    c_next = prices[k + 1]
                    if range_low - tol <= c_next <= range_high + tol:
                        fail_count += 1

        tests_of_range_high = hits_high
        tests_of_range_low = hits_low
        breakout_attempts = attempts
        if attempts > 0:
            breakout_fail_ratio = fail_count / attempts
        else:
            breakout_fail_ratio = 0.0

    # time_in_range_bars：非常粗略 —— 如果 overlap 高 & range_height 在合理区间，就加一
    # 真正的“在 range 中待了多久”以后可以用 regime 连续性来算
    time_in_range_bars = 0  # 先留0，后面可以做更复杂版本
    barbwire_score = 0.0    # TODO: 可以基于很多 doji + 小 range 来估计

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


# ---------- ReversalSignals（初版） ----------

def compute_reversal_signals(
    df: pd.DataFrame,
    i: int,
    atr_series: pd.Series,
    swing_struct: SwingStructure,
    local_trend: LocalTrendStats,
) -> ReversalSignals:
    """
    初版：不做精确的趋势线/通道，只先实现：
    - climax_runup_score
    - higher_low_score / lower_high_score
    - high1/2 / low1/2 的简易节奏检测
    其余先留 0 或 TODO。
    """
    atr_val = float(atr_series.iloc[i]) if not np.isnan(atr_series.iloc[i]) else 0.0

    # ===== climax_runup_score =====
    # 用：range_rel_atr 大 + 连续 trend bar + spike_strength 来近似
    # 需要最近 N 根 bar 的信息
    lookback = 20
    start_idx = max(0, i - lookback + 1)
    window = df.iloc[start_idx : i + 1]
    # 简单用高 ATR + 大实体 bar个数占比估计 climax
    big_range_count = 0
    trend_bar_count = 0
    for j in range(start_idx, i + 1):
        row = df.iloc[j]
        hi, lo = row["high"], row["low"]
        rng = hi - lo
        if atr_val > 0 and rng / atr_val > 1.5:
            big_range_count += 1
        if row["close"] > row["open"] and (row["close"] - row["open"]) > 0.6 * rng:
            trend_bar_count += 1
        if row["close"] < row["open"] and (row["open"] - row["close"]) > 0.6 * rng:
            trend_bar_count += 1
    nwin = max(1, i + 1 - start_idx)
    climax_runup_score = float(
        np.clip((big_range_count / nwin) * 0.6 + (trend_bar_count / nwin) * 0.4, 0.0, 1.0)
    )

    # ===== higher_low_score / lower_high_score =====
    higher_low_score = 0.0
    lower_high_score = 0.0
    # 粗略地用 swing_struct 中 last 两个腿数据判断：
    # 若 swing_direction 向上 且 leg2 更短，可能形成 HL；向下类似 LH
    if swing_struct.swing_direction > 0 and swing_struct.swing_leg2_size > 0:
        # 上涨后回调浅一些 → HL 倾向
        if swing_struct.leg2_vs_leg1_ratio < 0.7:
            higher_low_score = float(np.clip(1.0 - swing_struct.leg2_vs_leg1_ratio, 0.0, 1.0))
    elif swing_struct.swing_direction < 0 and swing_struct.swing_leg2_size > 0:
        if swing_struct.leg2_vs_leg1_ratio < 0.7:
            lower_high_score = float(np.clip(1.0 - swing_struct.leg2_vs_leg1_ratio, 0.0, 1.0))

    # ===== High1/High2/Low1/Low2 =====
    # 非常简化：通过 recent swing 推动力次数来 rough 标记：
    high1_score = 0.0
    high2_score = 0.0
    low1_score = 0.0
    low2_score = 0.0

    # 如果 wedge_push_count == 1/2/3，可以粗略当成一推/二推/三推
    if swing_struct.wedge_push_count == 1:
        if swing_struct.swing_direction > 0:
            high1_score = 0.5
        elif swing_struct.swing_direction < 0:
            low1_score = 0.5
    elif swing_struct.wedge_push_count == 2:
        if swing_struct.swing_direction > 0:
            high2_score = 0.7
        elif swing_struct.swing_direction < 0:
            low2_score = 0.7
    elif swing_struct.wedge_push_count >= 3:
        if swing_struct.swing_direction > 0:
            high2_score = 0.9
        elif swing_struct.swing_direction < 0:
            low2_score = 0.9

    # ===== 其他高级信号暂时置 0，后续可以专门做 =====
    trendline_break_score = 0.0      # TODO: 回头用回归线 + 当前价距离计算
    channel_overshoot_score = 0.0    # TODO: 用平行通道线超越程度
    pullback_after_climax_bars = 0   # TODO: 标记 climax 之后的 bar 数
    final_flag_score = 0.0           # TODO: 趋势末端小区间假突破的形态评分

    return ReversalSignals(
        trendline_break_score=float(trendline_break_score),
        channel_overshoot_score=float(channel_overshoot_score),
        climax_runup_score=float(climax_runup_score),
        pullback_after_climax_bars=int(pullback_after_climax_bars),
        higher_low_score=float(higher_low_score),
        lower_high_score=float(lower_high_score),
        high1_score=float(high1_score),
        high2_score=float(high2_score),
        low1_score=float(low1_score),
        low2_score=float(low2_score),
        final_flag_score=float(final_flag_score),
    )


# ---------- RiskRewardMetrics（初版） ----------

def compute_risk_reward(
    df: pd.DataFrame,
    i: int,
    atr_series: pd.Series,
    swing_struct: SwingStructure,
) -> RiskRewardMetrics:
    """
    初版：只计算简单的最近 swing 高低的距离 + 建议 stop 距离。
    真正 R:R 以后再细化。
    """
    atr_val = float(atr_series.iloc[i]) if not np.isnan(atr_series.iloc[i]) else 0.0
    if atr_val <= 0:
        atr_val = 1e-9

    # 最近 50 根里的 swing 高/低当作潜在 SR
    lookback = 50
    start_idx = max(0, i - lookback + 1)
    window = df.iloc[start_idx : i + 1]

    curr_price = float(df.iloc[i]["close"])

    recent_high = float(window["high"].max())
    recent_low = float(window["low"].min())

    nearest_resistance_dist = max(0.0, (recent_high - curr_price) / atr_val)
    nearest_support_dist = max(0.0, (curr_price - recent_low) / atr_val)

    # stop_distance：简单设为 1 ATR
    stop_distance_suggested = 1.0

    scalp_target_dist = 1.0   # 1R 目标
    swing_target_dist = 2.0   # 2R 目标（以后可根据 measured move 调）

    rr_swing_estimate = swing_target_dist / stop_distance_suggested if stop_distance_suggested > 0 else 0.0
    rr_scalp_estimate = scalp_target_dist / stop_distance_suggested if stop_distance_suggested > 0 else 0.0

    # 这三个概率先留 0，后续可用小模型或 heuristic 填
    prob_trend_continuation = 0.0
    prob_reversal = 0.0
    prob_range_continuation = 0.0

    return RiskRewardMetrics(
        nearest_support_dist=float(nearest_support_dist),
        nearest_resistance_dist=float(nearest_resistance_dist),
        stop_distance_suggested=float(stop_distance_suggested),
        scalp_target_dist=float(scalp_target_dist),
        swing_target_dist=float(swing_target_dist),
        rr_swing_estimate=float(rr_swing_estimate),
        rr_scalp_estimate=float(rr_scalp_estimate),
        prob_trend_continuation=float(prob_trend_continuation),
        prob_reversal=float(prob_reversal),
        prob_range_continuation=float(prob_range_continuation),
    )


# ---------- RegimeScores ----------

def compute_regime_scores(
    local_trend: LocalTrendStats,
    trading_range: RangeStructure,
) -> RegimeScores:
    """
    用简单 heuristic 给趋势/震荡打分。
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

    # 反转 / breakout 先简单放 0，后续加
    reversal_setup_score = 0.0
    breakout_mode_score = 0.0

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
