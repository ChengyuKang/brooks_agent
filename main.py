import pandas as pd
from dataclasses import asdict
import json

from ai_brooks_features import build_market_snapshots

df = pd.read_csv("ES_5m.csv", parse_dates=["timestamp"])

snapshots = build_market_snapshots(df, symbol="ES", timeframe_minutes=5)

print("total snapshots:", len(snapshots))

# 看一条
print(json.dumps(asdict(snapshots[0]), default=str, indent=2))
