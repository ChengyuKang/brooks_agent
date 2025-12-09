# Reversals, Major Trend Reversals, and Final Flags

This document covers how trends end and reverse.

## 1. Climax

A **buy climax** often shows:

- Many bull trend bars in a row.  
- Small or no pullbacks.  
- Gaps between price and EMA (moving average gap bars).  
- Price accelerating into resistance or a measured move target.

A **sell climax** is the mirror.

After a climax, the market often:

- Trades sideways to down (after a buy climax) or sideways to up (after a sell climax),  
- Forms a trading range,  
- Sometimes reverses the trend.

Feature hint: `climax_runup_score` measures how climactic the recent move is.

## 2. Major Trend Reversal (MTR) Structure

A major trend reversal usually has:

1. A prior strong trend (not just a small move).  
2. A final push or climax in the trend direction.  
3. A break of the trend line or channel line.  
4. A test of the prior extreme (double top/bottom, wedge push, or overshoot).  
5. A clear, strong signal bar in the opposite direction at or near that test.  
6. Reasonable follow-through in the new direction.

Not every reversal is an MTR; many are just pullbacks or transitions into a range.

## 3. Wedges

- A **wedge top** is typically three pushes up with decreasing momentum or increased overlap.  
- A **wedge bottom** is three pushes down with similar characteristics.  
- Wedges often lead to a reversal to at least a trading range and sometimes to an opposite trend.

Feature hints:

- `wedge_push_count` counts pushes (1, 2, 3+).  
- `wedge_score` measures how clearly the pattern looks like a wedge structure.  
- `channel_overshoot_score` measures how far price has moved beyond a channel line.

## 4. Double Tops and Double Bottoms

- **Double top**: two highs at roughly the same level, often after an uptrend or rally.  
- **Double bottom**: two lows at roughly the same level, after a downtrend or sell-off.  
- They can mark the end of a trend leg or the edges of a trading range.

Feature hints:

- `double_top_score` and `double_bottom_score` measure how clearly the pattern appears.

## 5. Final Flags

- A final flag is a small trading range or flag late in a trend that acts as a final pause before reversal.  
- Breakouts from final flags often fail and lead to a trend change or larger reversal.

Feature: `final_flag_score` reflects how likely the recent structure looks like a final flag.

## 6. Reversal Trade Quality

The agent should treat reversals as follows:

- Reversal attempts after weak trends or in the middle of ranges are low probability.  
- Reversals after clear trends, climaxes, and good structure (MTR, wedge, double top/bottom) have higher probability and better R:R.  
- Often the initial target for a reversal is a trading range, not a huge opposite trend.

Use `reversal_setup_score`, `prob_reversal`, and pattern scores to determine whether a reversal trade is appropriate and whether it should be a scalp or a swing.
