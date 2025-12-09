# decision_types.py
"""
决策层用到的 dataclass + 辅助函数：
- AccountState: 账户资金和风险参数
- PositionState: 当前持仓状态
- RecentTradesSummary: 当日交易统计，用于控制节奏
- PriceContext: 决策需要的关键原始量（价格、日高低等）
- DecisionRequest: 发给 LLM/RAG 的统一请求结构
- build_price_context_from_df: 从 df + snapshot 构造 PriceContext
- build_decision_request: 快速拼出完整 DecisionRequest
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from ai_brooks_features.schema import MarketSnapshot
from ai_brooks_features.config import ATR_PERIOD
from ai_brooks_features.indicators import atr


NY_TZ = ZoneInfo("America/New_York")


# ======================
# 账户 / 仓位 / 交易状态
# ======================

@dataclass
class AccountState:
    equity: float                        # 当前权益，例如 1000.0
    max_risk_per_trade_r: float = 1.0    # 单笔最大风险R（比如 1R = 账户1%）
    max_daily_loss_r: float = 3.0        # 当日最大亏损R
    realized_pnl_r_today: float = 0.0    # 当日已实现盈亏（按R计）


@dataclass
class PositionState:
    has_open_position: bool = False
    side: Optional[str] = None           # "long" / "short" / None
    entry_price: Optional[float] = None
    stop_price: Optional[float] = None
    target_price_1: Optional[float] = None
    target_price_2: Optional[float] = None
    size_contracts: Optional[float] = None
    time_in_bars: int = 0                # 已持有多少bar
    unrealized_r: Optional[float] = None # 当前浮盈/亏（按R）


@dataclass
class RecentTradesSummary:
    trades_today: int = 0                # 当日交易次数
    last_trade_outcome_r: Optional[float] = None  # 上一笔交易的结果（R）


# ======================
# 价格上下文（关键原始量）
# ======================

@dataclass
class PriceContext:
    current_price: float         # 当前bar收盘价
    current_atr: float           # 当前ATR值
    day_open: float              # 当日开盘价
    day_high: float              # 当日最高价
    day_low: float               # 当日最低价
    recent_swing_high: float     # 最近一段内的 swing high（近N根的最高价）
    recent_swing_low: float      # 最近一段内的 swing low（近N根的最低价）


# ======================
# 决策请求结构
# ======================

@dataclass
class DecisionRequest:
    snapshot: MarketSnapshot
    account: AccountState
    position: PositionState
    price_ctx: PriceContext
    trades_summary: RecentTradesSummary


# ======================
# 构造 PriceContext
# ======================

def _ensure_timestamp_series(df: pd.DataFrame) -> pd.Series:
    """
    保证我们有一个 tz-aware 的纽约时间戳 Series，方便按交易日分组。
    """
    if "timestamp" in df.columns:
        ts = pd.to_datetime(df["timestamp"])
    else:
        ts = pd.to_datetime(df.index.to_series())

    # 统一成纽约时间
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize(NY_TZ)
    else:
        ts = ts.dt.tz_convert(NY_TZ)

    return ts


def build_price_context_from_df(
    df: pd.DataFrame,
    snapshot: MarketSnapshot,
    atr_period: int = ATR_PERIOD,
    swing_lookback_bars: int = 50,
) -> PriceContext:
    """
    给定原始 OHLCV df + 对应的 MarketSnapshot，
    构造一个 PriceContext，提供决策层需要的关键原始量。

    要求：
    - df 至少包含 open/high/low/close 列
    - snapshot.meta.bar_index 必须是这条bar在 df 中的行号
    """
    if snapshot.meta.bar_index < 0 or snapshot.meta.bar_index >= len(df):
        raise IndexError(
            f"snapshot.meta.bar_index={snapshot.meta.bar_index} 超出 df 范围 (len(df)={len(df)})"
        )

    # 复制一份，避免修改原 df
    df_local = df.copy()

    # 准备带时区的 timestamp
    ts_series = _ensure_timestamp_series(df_local)
    df_local["timestamp"] = ts_series

    i = snapshot.meta.bar_index
    row = df_local.iloc[i]

    # 当前收盘价
    current_price = float(row["close"])

    # 计算全局 ATR 一次（可以后续优化成预先传入）
    atr_series = atr(df_local, period=atr_period)
    current_atr = float(atr_series.iloc[i])

    # 当日开盘 / 最高 / 最低
    ny_date = df_local["timestamp"].iloc[i].date()
    day_mask = df_local["timestamp"].dt.date == ny_date
    day_df = df_local.loc[day_mask]

    if day_df.empty:
        # 理论上不会发生，防御一下
        day_open = current_price
        day_high = current_price
        day_low = current_price
    else:
        day_open = float(day_df["open"].iloc[0])
        day_high = float(day_df["high"].max())
        day_low = float(day_df["low"].min())

    # 最近一段 swing 高低（简单用近 N 根的最高/最低）
    start_idx = max(0, i - swing_lookback_bars + 1)
    win_df = df_local.iloc[start_idx : i + 1]
    recent_swing_high = float(win_df["high"].max())
    recent_swing_low = float(win_df["low"].min())

    return PriceContext(
        current_price=current_price,
        current_atr=current_atr,
        day_open=day_open,
        day_high=day_high,
        day_low=day_low,
        recent_swing_high=recent_swing_high,
        recent_swing_low=recent_swing_low,
    )


# ======================
# 构造 DecisionRequest
# ======================

def build_decision_request(
    df: pd.DataFrame,
    snapshot: MarketSnapshot,
    account: AccountState,
    position: PositionState,
    trades_summary: Optional[RecentTradesSummary] = None,
) -> DecisionRequest:
    """
    外部调用入口：
    - df: 原始 OHLCV（和 build_market_snapshots 用的是同一个源）
    - snapshot: 最新的 MarketSnapshot
    - account: 当前账户状态
    - position: 当前持仓状态
    - trades_summary: 当日交易概况（可选）
    """
    price_ctx = build_price_context_from_df(df, snapshot)

    if trades_summary is None:
        trades_summary = RecentTradesSummary()

    return DecisionRequest(
        snapshot=snapshot,
        account=account,
        position=position,
        price_ctx=price_ctx,
        trades_summary=trades_summary,
    )
