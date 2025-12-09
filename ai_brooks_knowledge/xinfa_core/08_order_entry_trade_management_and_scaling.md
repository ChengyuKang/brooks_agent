# Order Entry, Trade Management, and Scaling

This document covers how to enter, manage, and exit trades.

## 1. Entry Types

Three basic entry types:

1. **Stop entry** – enter on a breakout beyond a bar or level.  
   - Use when expecting momentum continuation.  
2. **Limit entry** – enter on a pullback to a better price.  
   - Use when fading ranges or entering pullbacks in trends.  
3. **Market entry** – enter immediately at current price.  
   - Use when delay is costly and slippage is acceptable.

The agent’s decision schema can express “entry_type” as `market`, `stop`, or `limit` and describe the logic. Python then computes precise prices.

## 2. Stop Placement

- Stops should be placed where the trade idea is clearly wrong:  
  - Beyond the signal bar’s extreme plus a cushion.  
  - Outside the recent swing high/low or range edge.  
- Avoid arbitrary “money stops” that ignore structure.

In features:

- `nearest_support_dist` / `nearest_resistance_dist`  
- `stop_distance_suggested` expressed in ATR multiples.

The agent should suggest stop placement in terms of “above/below swing/structure” plus an ATR buffer, not exact prices.

## 3. Targets: Scalps vs Swings

- **Scalp targets**:  
  - Small, quick profits; often 1R or less.  
  - Magnet-based (EMA, mid-range, minor level).  
- **Swing targets**:  
  - Larger moves; 2R or more.  
  - Opposite side of range, measured move targets, or major support/resistance.

The snapshot’s `rr_scalp_estimate` and `rr_swing_estimate` help classify whether scalp or swing trades are realistic.

## 4. Position Sizing

- Compute position size from risk:  
  - Position size = (allowed money risk per trade) / (risk per share or per point).  
- The agent should keep size fixed in R units, not scaled up “by feeling.”

## 5. Scaling In and Out

- **Scaling in**:  
  - Adding to a winning position in a strong trend can be reasonable if risk remains under control.  
  - Adding to a losing position is dangerous; the agent should avoid “averaging down” in this MVP.

- **Scaling out**:  
  - Taking partial profits at the first target, moving the stop to breakeven on the remainder.  
  - Useful to lock in gains while still participating in a potential larger move.

The agent’s management plan can include actions like `reduce_position`, `move_stop`, and `exit_now`.

## 6. Daily Risk and Stopping Rules

- The agent must respect daily loss limits, e.g., no more trades after losing 3R in a day.  
- After a sequence of losses, it may reduce size or switch to observation-only mode.

Trade management is as important as entry; “good management of a mediocre entry” often beats “poor management of a good entry.”
