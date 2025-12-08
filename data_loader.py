# data_loader.py
"""
数据加载工具：
- 从 yfinance 下载 SPY / 其他标的 5m 数据
- 从本地 CSV 加载 OHLCV，并转换成统一格式
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


try:
    import yfinance as yf
except ImportError as e:
    yf = None


# =========================
# 配置 & 小工具
# =========================

@dataclass
class DataConfig:
    symbol: str = "SPY"
    interval: str = "5m"          # yfinance: 1m,2m,5m,15m,...
    period: str = "60d"           # 60d, 30d, 1y, max ...
    timezone: str = "America/New_York"        

def _standardize_ohlcv_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    把各种来源的 OHLCV DataFrame 统一成：
    index: DatetimeIndex
    columns: ["open", "high", "low", "close", "volume"]
    """
    if df is None or df.empty:
        raise ValueError("DataFrame is empty.")

    # 如果有 timestamp 列，尝试用它做 index
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp")

    # yfinance 有时会返回 MultiIndex 列（如 ('Open', 'SPY')），先拍平成字符串
    if isinstance(df.columns, pd.MultiIndex):
        ohlcv_aliases = {"open", "high", "low", "close", "adj close", "adjclose", "volume", "vol"}

        def _flatten_col(col: tuple) -> str:
            # 优先找出符合 OHLCV 名称的那一段
            for part in col:
                if isinstance(part, str) and part.strip().lower() in ohlcv_aliases:
                    return part

            parts = [str(p) for p in col if p not in (None, "")]
            return parts[0] if parts else "unknown"

        df.columns = [_flatten_col(col) for col in df.columns]

    # 统一列名为小写
    rename_map = {}
    for col in df.columns:
        lc = str(col).lower()
        if lc in ["open", "high", "low", "close", "volume"]:
            rename_map[col] = lc
        elif lc in ["vol", "volume"]:
            rename_map[col] = "volume"
    df = df.rename(columns=rename_map)

    required_cols = {"open", "high", "low", "close", "volume"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"DataFrame missing required columns: {required_cols - set(df.columns)}")

    # 只保留需要的列，按顺序
    df = df[["open", "high", "low", "close", "volume"]].copy()

    # 确保 index 是 DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("DataFrame index must be DatetimeIndex or there must be a 'timestamp' column.")

    # 排序
    df = df.sort_index()

    return df


# =========================
# 从 yfinance 下载数据
# =========================

def download_ohlcv_yfinance(
    symbol: str = "SPY",
    interval: str = "5m",
    period: str = "60d",
    tz: str = "America/New_York",        # 默认纽约
) -> pd.DataFrame:
    """
    用 yfinance 下载 OHLCV 数据，并标准化成统一格式。

    参数示例:
        symbol="SPY", interval="5m", period="60d"
    """
    if yf is None:
        raise ImportError(
            "yfinance is not installed. Run: pip install yfinance"
        )

    df = yf.download(symbol, interval=interval, period=period)
    if df is None or df.empty:
        raise RuntimeError(f"Failed to download data for symbol={symbol}, interval={interval}, period={period}")

    # yfinance 返回的列通常是: Open, High, Low, Close, Adj Close, Volume
    df = _standardize_ohlcv_df(df)

    # yfinance 的 index 通常已经是 America/New_York
    if df.index.tz is None:
        # 万一没 tz，就先当成纽约
        df = df.tz_localize("America/New_York")
    else:
        df = df.tz_convert("America/New_York")

    # 如果用户指定了别的 tz，再转
    if tz != "America/New_York":
        df = df.tz_convert(tz)

    return df


# =========================
# 从 CSV 加载数据
# =========================

def load_ohlcv_from_csv(
    path: str,
    timestamp_col: Optional[str] = "timestamp",
    tz: str = "America/New_York",
) -> pd.DataFrame:
    """
    从本地 CSV 加载 OHLCV 数据，并标准化成统一格式。

    要求 CSV 至少有:
        - 一个时间列 (默认 'timestamp') 或 index 可转成 datetime
        - open, high, low, close, volume 这些列（可大小写混合）

    示例 CSV 结构:
        timestamp,open,high,low,close,volume
        2024-01-01 14:30:00, ..., ..., ..., ..., ...

    或:
        index 是 datetime，列名是 Open, High, Low, Close, Volume
    """
    df = pd.read_csv(path)

    if timestamp_col in df.columns:
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        df = df.set_index(timestamp_col)

    df = _standardize_ohlcv_df(df)

    if df.index.tz is None:
        df = df.tz_localize("America/New_York")
    else:
        df = df.tz_convert("America/New_York")

    if tz != "America/New_York":
        df = df.tz_convert(tz)

    return df


# =========================
# 简单封装：专门为 SPY / ES MVP 用
# =========================

def load_spy_5m_for_mvp(
    period: str = "60d",
    tz: str = "America/New_York",
) -> pd.DataFrame:
    cfg = DataConfig(symbol="SPY", interval="5m", period=period, timezone=tz)
    df = download_ohlcv_yfinance(cfg.symbol, cfg.interval, cfg.period, cfg.timezone)
    return df
