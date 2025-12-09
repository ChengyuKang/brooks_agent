# Multi-Timeframe Context and Regime Transitions

This document explains how smaller trends and ranges fit into larger structures.

## 1. Fractal Nature of Price Action

- Patterns repeat across timeframes: a 5-minute chart often looks like a compressed version of a 60-minute or daily chart.  
- A trading range on a lower timeframe may be a pullback on a higher timeframe.  
- A simple leg up on a higher timeframe may look like a complex trend with many pullbacks on a lower timeframe.

For the agent, we approximate higher timeframe context via regime and swing features in the 5-minute data.

## 2. Trend → Range → Reversal Cycle

Markets often move through this cycle:

1. **Trend phase** – strong directional movement.  
2. **Trading range phase** – volatility and overlap increase; market oscillates.  
3. **Reversal or resumption** – either a major reversal or a breakout to resume the trend.

Transitions are visible when:

- `trending_score` gradually falls and `ranging_score` rises.  
- Pullbacks become deeper and longer.  
- Breakouts fail more often near prior extremes.

## 3. Range as a Higher-Timeframe Pullback

- A trading range on 5-minute may represent a pullback or consolidation on 60-minute or daily charts.  
- In that context, range breakouts that align with the higher timeframe trend are more likely to succeed.  
- Opposite direction breakouts may be only short-lived reversals.

## 4. Using Swing Structure as a Proxy for Higher Timeframe

Your swing features approximate higher timeframe moves:

- `swing_direction` (+1 up, -1 down) indicates the direction of recent legs.  
- `swing_leg1_size` and `swing_leg2_size` show leg magnitudes relative to ATR.  
- `leg2_vs_leg1_ratio` hints at acceleration or loss of momentum.  
- `hh_ll_score` captures higher-high/higher-low or lower-high/lower-low structure.

The agent can:

- Treat a large upswing (`swing_leg2_size` >> ATR) as a higher timeframe leg.  
- Consider a developing trading range as a potential base for the next leg in the same direction or a base for a reversal.

## 5. Regime Transitions in Practice

Typical signs of a trend turning into a range:

- Increased overlap and dojis.  
- Fewer closes near trend extremes.  
- Strong countertrend bars at or near prior extremes.  
- Failure of breakout attempts beyond prior highs/lows.

Typical signs of a range breaking into a trend:

- Strong breakout bar beyond the range edge.  
- Follow-through in the same direction.  
- Rejection of attempts to return inside the range.

The agent should monitor evolving regime scores and adjust expectations and trade types accordingly.
