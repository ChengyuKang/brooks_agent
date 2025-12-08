# ai_brooks_features/builder.py
from __future__ import annotations

from typing import List
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
    empty_swing_structure,
    empty_reversal_signals,
    empty_risk_reward,
    compute_regime_scores,
)

NY_TZ = ZoneInfo("America/New_York")


def build_market_snapshots(
    df: pd.DataFrame,
    symbol: str,
    timeframe_minutes: float,
) -> List[MarketSnapshot]:
    """
    从 OHLCV DataFrame 构建一串 MarketSnapshot。

    要求 df 至少有: ["open", "high", "low", "close", "volume"]。
    index 或 "timestamp" 列中需要有 datetime 信息。
    这里所有与“日内时间 / 交易日”相关的逻辑，都按纽约时间 (America/New_York) 处理。
    """
    df = df.copy()

    # 1) 处理时间戳：拿到一个 Series，后面统一转成纽约时间
    if "timestamp" in df.columns:
        ts_series = pd.to_datetime(df["timestamp"])
    else:
        ts_series = pd.to_datetime(df.index)

    # 确保有时区：如果没有，就假定已经是纽约时间本地化；如果有，就转成纽约时间
    if ts_series.dt.tz is None:
        ts_series = ts_series.dt.tz_localize("America/New_York")
    else:
        ts_series = ts_series.dt.tz_convert("America/New_York")

    # 把处理好的时间戳塞回 df
    df["timestamp"] = ts_series

    # 为了按“纽约日期”计算 day_index，再单独保留一份
    ts_series_ny = ts_series  # 现在已经是 NY TZ 了

    # 2) 预计算 ATR / EMA / volume zscore 等指标
    df = precompute_indicators(df)
    atr_series = df["atr"]
    ema_series = df["ema"]

    snapshots: List[MarketSnapshot] = []

    # 3) 为了有足够 lookback，从 max(...) 之后开始
    start_i = max(ATR_PERIOD, TREND_LOOKBACK, RANGE_LOOKBACK) + 1

    for i in range(start_i, len(df)):
        row = df.iloc[i]
        # row["timestamp"] 已经是 tz-aware 的 pandas.Timestamp
        ts: datetime = row["timestamp"].to_pydatetime()

        # —— meta context（按纽约交易日拆分）——
        ny_date = ts_series_ny.iloc[i].date()          # 当前这个bar的纽约日期
        same_day_mask = ts_series_ny.dt.date == ny_date
        day_indices = np.where(same_day_mask.values)[0]

        # day_index = 当天从 0 开始的 bar 序号
        day_index = int(np.where(day_indices == i)[0][0]) if i in day_indices else 0

        meta = MetaContext(
            timestamp=ts,                    # 保留原来的 timestamp（带 tz）
            symbol=symbol,
            day_index=day_index,
            session=infer_session(ts),       # 内部会用纽约时间判断 RTH / ETH
            day_of_week=int(ts.astimezone(NY_TZ).weekday()),
        )

        # —— 各模块特征 ——
        bar_stats = compute_bar_stats(df, i, atr_series)
        local_trend = compute_local_trend_stats(df, i, ema_series, atr_series)
        range_struct = compute_range_structure(df, i, atr_series)

        swing_struct = empty_swing_structure()        # TODO: 后续实现 swing 结构
        reversal_signals = empty_reversal_signals()   # TODO
        risk_reward = empty_risk_reward()             # TODO

        regime_scores = compute_regime_scores(local_trend, range_struct)

        # 日内时间位置（0~1），内部也会用纽约时间
        tod_frac = time_of_day_fraction(ts)

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
