# ai_brooks_features/builder.py
from __future__ import annotations

from typing import List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .schema import MarketSnapshot, MetaContext
from .config import ATR_PERIOD, TREND_LOOKBACK, RANGE_LOOKBACK
from .indicators import time_of_day_fraction, infer_session
from .feature_calculators import (
    precompute_indicators,
    compute_bar_stats,
    compute_local_trend_stats,
    compute_range_structure,
    compute_swing_structure,
    compute_reversal_signals,
    compute_risk_reward,
    compute_regime_scores,
)

NY_TZ = ZoneInfo("America/New_York")


def build_market_snapshots(
    df: pd.DataFrame,
    symbol: str,
    timeframe_minutes: float,
    only_last_n_bars: Optional[int] = None,  # 只算最近 N 根
    step: int = 1,                            # 每隔 step 根取一个 snapshot
) -> List[MarketSnapshot]:
    """
    从 OHLCV DataFrame 构建一串 MarketSnapshot。

    要求 df 至少有: ["open", "high", "low", "close", "volume"]。
    index 或 "timestamp" 列中需要有 datetime 信息。

    参数:
        only_last_n_bars:   如果不为空，只对最近 N 根 bar 计算 snapshot
        step:               间隔多少根算一个 snapshot（1 = 每根都算）
    """
    df = df.copy()

    # ========= 处理时间戳成纽约时间 =========
    if "timestamp" in df.columns:
        ts_series = pd.to_datetime(df["timestamp"])
    else:
        # index -> Series，这样才能用 .dt
        ts_series = pd.to_datetime(df.index.to_series())

    # 统一成 tz-aware Series（纽约时间）
    if ts_series.dt.tz is None:
        ts_series = ts_series.dt.tz_localize(NY_TZ)
    else:
        ts_series = ts_series.dt.tz_convert(NY_TZ)

    # ✅ 关键：直接用 Series，别用 .values
    df["timestamp"] = ts_series
    ts_series_ny = ts_series  # Series, index 对齐 df

    # ========= 预计算指标 =========
    df = precompute_indicators(df)
    atr_series = df["atr"]
    ema_series = df["ema"]

    n = len(df)
    snapshots: List[MarketSnapshot] = []

    # 至少要有这么多 bar 才能算 ATR / trend / range
    base_start = max(ATR_PERIOD, TREND_LOOKBACK, RANGE_LOOKBACK) + 1

    # 如果只需要最近 N 根，就把起点往后推
    if only_last_n_bars is not None:
        base_start = max(base_start, n - only_last_n_bars)

    start_i = min(base_start, n - 1)

    # ========= 主循环 =========
    for i in range(start_i, n, step):
        row = df.iloc[i]
        ts: pd.Timestamp = row["timestamp"]  # tz-aware, 在 America/New_York

        # ---- meta context ----
        ny_ts = ts  # 已经是纽约时间

        # 这一天里的第几根 bar（按纽约日期）
        ny_date = ts_series_ny.iloc[i].date()
        same_day_mask = ts_series_ny.dt.date == ny_date
        day_indices = np.where(same_day_mask.values)[0]
        if i in day_indices:
            day_index = int(np.where(day_indices == i)[0][0])
        else:
            day_index = 0

        py_dt = ny_ts.to_pydatetime()  # tz-aware python datetime

        meta = MetaContext(
            timestamp=py_dt,
            symbol=symbol,
            day_index=day_index,
            session=infer_session(py_dt),          # infer_session 内部也按 NY 处理
            day_of_week=int(ny_ts.weekday()),
            bar_index=i,   
        )

        # ---- 各模块特征 ----
        bar_stats = compute_bar_stats(df, i, atr_series)
        local_trend = compute_local_trend_stats(df, i, ema_series, atr_series)
        range_struct = compute_range_structure(df, i, atr_series)
        swing_struct = compute_swing_structure(df, i, atr_series)
        reversal_signals = compute_reversal_signals(df, i, atr_series, swing_struct, local_trend)
        risk_reward = compute_risk_reward(df, i, atr_series, swing_struct)
        regime_scores = compute_regime_scores(local_trend, range_struct)

        tod_frac = time_of_day_fraction(py_dt)     # 用纽约时间算日内位置

        snapshot = MarketSnapshot(
            meta=meta,
            bar=bar_stats,
            local_trend=local_trend,
            swing=swing_struct,
            trading_range=range_struct,
            reversals=reversal_signals,
            risk_reward=risk_reward,
            regime=regime_scores,
            timeframe_minutes=timeframe_minutes,
            time_of_day_fraction=tod_frac,
        )
        snapshots.append(snapshot)

    return snapshots
