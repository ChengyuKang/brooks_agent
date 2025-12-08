# ai_brooks_features/schema.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class MetaContext:
    timestamp: datetime           # 当前 bar 结束时间
    symbol: str                   # ES / MES / SPY ...
    day_index: int                # 当天第几根 bar（从 0 开始）
    session: str                  # "RTH" / "ETH" / "UNKNOWN"
    day_of_week: int              # 0=Monday ... 6=Sunday


@dataclass
class BarStats:
    body_rel: float               # 实体占整个bar的比例 0~1
    upper_tail_rel: float         # 上影线比例 0~1
    lower_tail_rel: float         # 下影线比例 0~1
    close_pos_rel: float          # 收盘在bar内的位置 0~1
    range_rel_atr: float          # 当前bar振幅 / N-bar ATR
    gap_to_prev_close: float      # 距离前一bar收盘(以 ATR 为单位)
    is_trend_bar_score: float     # 趋势bar强度评分 0~1
    is_doji_score: float          # doji 评分 0~1
    is_outside_score: float       # outside bar 评分 0~1
    is_inside_score: float        # inside bar 评分 0~1
    volume_zscore: float          # 成交量z分数，0≈正常，>0放量


@dataclass
class LocalTrendStats:
    ema_slope: float              # 20EMA 斜率（标准化）
    bars_above_ema_ratio: float   # 过去N根中在EMA上方的比例
    consecutive_bull_bars: int    # 连续阳线数
    consecutive_bear_bars: int    # 连续阴线数
    micro_channel_bars: int       # 微通道长度（无/极少回调的连续bar数）
    pullback_depth_rel: float     # 最近一次回调深度/最近主趋势腿高度
    pullback_bars: int            # 最近回调持续bar数
    spike_strength: float         # 最近spike强度评分 0~1
    trend_persistence: float      # “always-in”趋势持续性评分 0~1


@dataclass
class SwingStructure:
    swing_direction: float        # 摆动方向：+1=上，-1=下，0=混沌
    hh_ll_score: float            # Higher High / Lower Low 结构评分 0~1
    swing_leg1_size: float        # 最近两腿长度（标准化到ATR）
    swing_leg2_size: float
    leg2_vs_leg1_ratio: float     # 第二腿/第一腿长度
    wedge_push_count: int         # 最近一段中的“推进次数”（1/2/3）
    wedge_score: float            # 楔形/三推结构评分 0~1
    double_top_score: float       # 双顶评分 0~1
    double_bottom_score: float    # 双底评分 0~1


@dataclass
class RangeStructure:
    overlap_ratio: float          # 最近N根bar之间的重叠比例 0~1
    range_height_rel_atr: float   # 当前震荡区高度/ATR
    time_in_range_bars: int       # 在当前震荡结构中停留的bar数
    tests_of_range_high: int      # 近期测试区间上沿的次数
    tests_of_range_low: int       # 近期测试区间下沿的次数
    breakout_attempts: int        # 最近N根里尝试突破（高/低点）的次数
    breakout_fail_ratio: float    # 突破失败占比 0~1
    barbwire_score: float         # “刺线/barbwire”模式评分 0~1


@dataclass
class ReversalSignals:
    trendline_break_score: float      # 最近是否刚刚有效跌破/突破趋势线 0~1
    channel_overshoot_score: float    # 通道超越程度（超出trend channel line）0~1
    climax_runup_score: float         # 连续climax/趋势bar的程度 0~1
    pullback_after_climax_bars: int   # climax后已经走了多少bar回调
    higher_low_score: float           # 潜在HL结构评分 0~1
    lower_high_score: float           # 潜在LH结构评分 0~1
    high1_score: float                # High 1 信号强度 0~1
    high2_score: float                # High 2 信号强度 0~1
    low1_score: float                 # Low 1 信号强度 0~1
    low2_score: float                 # Low 2 信号强度 0~1
    final_flag_score: float           # “最后旗形/终结形态”评分 0~1


@dataclass
class RiskRewardMetrics:
    nearest_support_dist: float       # 最近支撑距离（点数/ATR）
    nearest_resistance_dist: float
    stop_distance_suggested: float    # 典型保护止损距离（点数/ATR）
    scalp_target_dist: float          # 典型scalp目标距离（点数/ATR）
    swing_target_dist: float          # 典型swing目标距离（点数/ATR）
    rr_swing_estimate: float          # 粗略RR比 swing
    rr_scalp_estimate: float          # 粗略RR比 scalp
    prob_trend_continuation: float    # 主趋势延续概率粗估 0~1
    prob_reversal: float              # 趋势反转概率粗估 0~1
    prob_range_continuation: float    # 继续震荡概率粗估 0~1


@dataclass
class RegimeScores:
    trending_score: float             # “当前更像趋势”的评分 0~1
    ranging_score: float              # “更像震荡”的评分 0~1
    reversal_setup_score: float       # “正在形成反转setup”的评分 0~1
    breakout_mode_score: float        # “双向突破模式”的评分 0~1


@dataclass
class MarketSnapshot:
    meta: MetaContext
    bar: BarStats
    local_trend: LocalTrendStats
    swing: SwingStructure
    trading_range: RangeStructure
    reversals: ReversalSignals
    risk_reward: RiskRewardMetrics
    regime: RegimeScores
    timeframe_minutes: float          # e.g. 5 for 5min
    time_of_day_fraction: float       # 0~1 映射到日内时间
