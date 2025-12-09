# demo_build_snapshots.py
import json
from dataclasses import asdict

from data_loader import load_spy_5m_for_mvp
from ai_brooks_features.builder import build_market_snapshots
from decision_types import (          # 🔥 新增：引入决策相关类型
    AccountState,
    PositionState,
    RecentTradesSummary,
    build_decision_request,
)

# 1. 加载数据 & 构建 snapshots
df = load_spy_5m_for_mvp(period="60d")
print("Raw df shape:", df.shape)

snapshots = build_market_snapshots(
    df,
    symbol="SPY",
    timeframe_minutes=5,
    only_last_n_bars=None,  # 先算全部；你也可以设 2000 提速
)
print("Total snapshots:", len(snapshots))

# 2. 预设一个简单的账户 / 仓位 / 当日交易状态（你可以之后改成从真实状态读取）
default_account = AccountState(
    equity=1000.0,
    max_risk_per_trade_r=1.0,
    max_daily_loss_r=3.0,
    realized_pnl_r_today=0.0,
)

default_position = PositionState(
    has_open_position=False,
)

default_trades_summary = RecentTradesSummary(
    trades_today=0,
    last_trade_outcome_r=None,
)

# 3. 交互：输入 index 查看 snapshot + 对应的 DecisionRequest
while True:
    user_input = input("输入一个 snapshot index (或 'q' 退出): ")
    if user_input.lower() in ["q", "quit", "exit"]:
        break
    try:
        idx = int(user_input)
        if 0 <= idx < len(snapshots):
            snap = snapshots[idx]

            print(f"\n=== snapshot[{idx}] ===")
            print(json.dumps(asdict(snap), default=str, indent=2))

            # 🔥 额外构造并打印对应的 DecisionRequest
            decision_request = build_decision_request(
                df=df,
                snapshot=snap,
                account=default_account,
                position=default_position,
                trades_summary=default_trades_summary,
            )

            print(f"\n=== DecisionRequest for snapshot[{idx}] ===")
            print(json.dumps(asdict(decision_request), default=str, indent=2))

        else:
            print("index 越界啦。")
    except ValueError:
        print("请输入整数 index 或 q 退出。")
