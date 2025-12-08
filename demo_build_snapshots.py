# demo_build_snapshots.py
import json
from dataclasses import asdict

from data_loader import load_spy_5m_for_mvp
from ai_brooks_features.builder import build_market_snapshots

# 1. 加载 SPY 5 分钟数据（最近 60 天）
df = load_spy_5m_for_mvp(period="60d")
print("Raw df shape:", df.shape)
print(df.head(1))

# # 2. 构建 MarketSnapshot 序列
# snapshots = build_market_snapshots(df, symbol="SPY", timeframe_minutes=5)
# print("Total snapshots:", len(snapshots))

# # 3. 看一条 snapshot 长什么样（后面就可以直接给 RAG/LLM 用）
# first = snapshots[0]
# print(json.dumps(asdict(snapshots[4555]), default=str, indent=2))
4