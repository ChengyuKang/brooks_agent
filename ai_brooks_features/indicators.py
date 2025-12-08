# ai_brooks_features/indicators.py
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo  # Python 3.9+

import numpy as np
import pandas as pd

from .config import ATR_PERIOD, VOLUME_ZSCORE_LOOKBACK


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def volume_zscore(series: pd.Series, lookback: int = VOLUME_ZSCORE_LOOKBACK) -> pd.Series:
    rolling_mean = series.rolling(lookback).mean()
    rolling_std = series.rolling(lookback).std(ddof=0)
    z = (series - rolling_mean) / (rolling_std + 1e-9)
    return z


NY_TZ = ZoneInfo("America/New_York")


def time_of_day_fraction(ts: datetime) -> float:
    """
    按美股当地时间（纽约时间）算日内位置：
    0 = 当地 00:00, 1 = 当地 24:00
    """
    ny = ts.astimezone(NY_TZ)
    minutes = ny.hour * 60 + ny.minute
    return minutes / (24 * 60)


def infer_session(ts: datetime) -> str:
    """
    按美股 RTH 定义：
    纽约时间 09:30–16:00 为 RTH，其余为 ETH。
    """
    ny = ts.astimezone(NY_TZ)
    h, m = ny.hour, ny.minute

    # RTH: 09:30 <= time < 16:00
    after_open = (h > 9) or (h == 9 and m >= 30)
    before_close = h < 16  # 16:00 之后算 ETH

    if after_open and before_close:
        return "RTH"
    return "ETH"
