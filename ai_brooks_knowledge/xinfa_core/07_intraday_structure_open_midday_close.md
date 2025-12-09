# Intraday Structure: Open, Midday, and Close

This document describes how time of day affects intraday trading behavior.

## 1. Opening Phase

- The first 1–2 hours of the regular trading session (RTH) are usually the most volatile.  
- Common patterns:  
  - **Trend from the open** – strong trend bars and little overlap; may lead to a trend day.  
  - **Trading range open** – early range that later breaks out.  
  - **Opening reversal** – early breakout one way that quickly reverses and trends in the other direction.

The agent should:

- Pay attention to the early regime: is the open clearly trending or range-like?  
- Avoid fading a strong trend from the open until there is clear evidence of exhaustion or reversal.

## 2. Midday Phase

- Typically lower volume and more overlapping bars.  
- Many setups during midday are weak, and reward-to-risk is poorer.  
- The market often drifts sideways or forms tight trading ranges and small channels.

The agent should:

- Lower expectations during midday; consider smaller targets or fewer trades.  
- Avoid aggressive new swing positions unless the context is exceptional.

## 3. Late Session and Close

- The final hour can show strong moves as institutions reposition into the close.  
- Common behaviors:  
  - Tests of the day’s high/low.  
  - Reversals from extremes if trends are exhausted.  
  - Breakouts from intraday ranges that run into the close.

The agent should:

- Use `time_of_day_fraction` to recognize late-session conditions.  
- Be aware that closing moves can be fast and volatile.  
- Prefer clean setups that align with higher timeframe context or clear magnets (day high/low, prior day’s levels).

## 4. Time-of-Day Feature

In the snapshot:

- `time_of_day_fraction` maps the RTH session to a 0–1 scale:  
  - ~0.0–0.3: opening phase.  
  - ~0.3–0.7: midday.  
  - ~0.7–1.0: late session into the close.

The agent should adjust trade frequency, targets, and aggressiveness based on this time-of-day context.
