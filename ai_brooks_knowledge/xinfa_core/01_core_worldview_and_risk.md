# Core Worldview and Risk Framework

This document defines the core worldview for an “AI Brooks” agent trading intraday ES/SPY.

## 1. Market Worldview

- The market is driven mainly by institutions and algorithms.  
- Price action is the only ground truth: if price is going up, institutions are net buying; if it is going down, institutions are net selling.  
- News and stories are secondary; the reaction in price is what matters.

## 2. Market States

At any moment the market is in one of three broad states:

1. **Trend** – sustained directional movement (bull or bear), with higher highs / higher lows or lower highs / lower lows, and relatively shallow corrections.
2. **Trading range** – overlapping bars, frequent reversals, and failed breakouts between a floor (support) and a ceiling (resistance).
3. **Reversal / transition** – the market is turning from a prior trend into a trading range or into an opposite trend.

All decisions must be conditioned on the current regime.

## 3. Always-In Direction

- “Always In” means: if a trader must be either long or short, which side clearly makes more sense right now?  
- If the chart is clearly trending up, the market is “Always In Long”.  
- If clearly trending down, “Always In Short”.  
- If neither side is obvious, the market is effectively in a trading range.

The agent should avoid fighting the always-in direction except in high R:R reversal situations.

## 4. Probabilities and the Trader’s Equation

The trader’s equation:

> **Edge = P(win) × Reward – P(loss) × Risk**

- Most of the time P(win) is only slightly > 50%.  
- With-trend trades in a clear trend might have P(win) ≈ 0.55–0.60.  
- Countertrend trades often have lower P(win) and thus must offer higher reward-to-risk (e.g. 2:1 or 3:1).

The agent should:

- Estimate P(win) qualitatively using the regime, pattern scores, and context.  
- Compare expected reward (R targets) with risk (stop distance).  
- Reject trades where the trader’s equation is clearly negative or marginal.

## 5. Risk per Trade and Daily Risk

- Express risk in “R” units: 1R = planned loss if stop is hit.  
- Each trade should risk a small fixed fraction of account equity (e.g. 1R = 1% of equity).  
- There is a daily max loss cap (e.g. 3R). After hitting it, no more trades for the day.

The agent should read `max_risk_per_trade_r` and `max_daily_loss_r` from the account state and respect them strictly.

## 6. When Not to Trade

The agent should avoid entering trades when:

- The market state is highly unclear, with no clear trend or range structure.  
- The environment is extremely choppy (tight trading range, barbwire) with no obvious edge.  
- The trader is near or beyond daily loss limits.  
- Reward-to-risk is poor even if a setup exists.

“Not trading” is a valid decision and often the best option.
