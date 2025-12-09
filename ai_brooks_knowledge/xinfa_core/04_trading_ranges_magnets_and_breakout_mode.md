# Trading Ranges, Magnets, and Breakout Mode

This document describes how to interpret trading ranges, magnets, and breakout conditions.

## 1. Identifying a Trading Range

A trading range has:

- A ceiling (resistance) and a floor (support).  
- Many overlapping bars; high `overlap_ratio`.  
- Frequent reversals up and down.  
- Breakouts beyond the range edges that often fail and return inside.

Feature hints:

- `ranging_score` high.  
- `range_height_rel_atr` shows range height relative to volatility.  
- `tests_of_range_high` and `tests_of_range_low` count how often each edge has been tested.

## 2. Magnets

Common “magnets” in ranges:

- Range high and range low.  
- Midpoint of the range.  
- Prior day’s high/low and close.  
- Measured move targets based on range height.  
- EMA and other moving averages.

Price tends to oscillate between these magnets, especially in a mature range.

## 3. Trading Logic in Ranges

Default assumptions in a well-defined range:

- Expect reversals near the edges and two-sided trading inside.  
- Fading extremes (shorting near range highs, buying near range lows) can be profitable if:  
  - the range is mature,  
  - signal bars are good,  
  - risk is small relative to range height.

Targets:

- Scalps often aim for a move back toward the midpoint.  
- Swings can target the opposite side of the range.

## 4. Breakouts and Breakout Mode

- **Breakout**: a move outside the range high/low.  
- A good breakout often has:  
  - a strong trend bar closing beyond the range,  
  - follow-through in the next bar(s),  
  - increased volume and volatility.

- **Failed breakout**:  
  - price quickly reverses back into the range, trapping breakout traders.

**Breakout mode**:

- Market is coiling in a tight zone, often with ii / iii / ioi patterns.  
- A strong move can break out in either direction.  
- Both bulls and bears may have reasonable arguments; risk is higher.

In features:

- `breakout_mode_score` marks compression / breakout-ready conditions.  
- `barbwire_score` warns of noisy, overlapping bars with poor R:R.

The agent should:

- Prefer fading range extremes once the range is mature.  
- Be cautious trading breakouts unless breakout strength and context are clearly favorable.  
- Avoid trading in very tight, noisy consolidation unless risk is tiny and reward is clear.
