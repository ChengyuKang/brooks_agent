# Bar Language and Micro Patterns

This document explains how to interpret individual bars and small bar sequences.

## 1. Bar Anatomy

Each bar has:

- **Body** – distance between open and close.  
- **Upper tail** – high minus max(open, close).  
- **Lower tail** – min(open, close) minus low.  
- **Close position** – where the close sits within the bar (near high, middle, or low).  
- **Volume** – relative participation.

In the feature snapshot:

- `body_rel` is body size as a fraction of total range.  
- `upper_tail_rel` and `lower_tail_rel` describe wick proportions.  
- `close_pos_rel` locates the close inside the range.  
- `volume_zscore` measures how unusual the volume is.

## 2. Basic Bar Types

1. **Strong trend bar**  
   - Large body, close near high (bull) or low (bear), small opposite tail.  
   - Indicates aggressive activity by one side.  
   - Often leads to at least one more bar in the same direction, especially in a trend.

2. **Doji**  
   - Small body, often with tails on both sides.  
   - Represents short-term indecision or balance.  
   - In a strong trend, dojis are usually pauses, not reversals by themselves.

3. **Reversal bar (signal bar)**  
   - For bull reversal: a bar with a tail below and close near the top, appearing after a decline or test of support.  
   - For bear reversal: tail on top, close near the low, after a rally or test of resistance.  
   - Strength increases with bar size, location at an extreme, and good follow-through.

4. **Outside bar**  
   - High above prior bar’s high, low below prior bar’s low.  
   - Expands volatility; a sign of strong disagreement.  
   - Can be a trap or a strong breakout, depending on context.

5. **Inside bar**  
   - High below prior high and low above prior low.  
   - Contraction; often part of a breakout mode pattern.

## 3. Micro Patterns

- **ii / iii**  
  - Two or three consecutive inside bars.  
  - Compression; breakout mode where a strong move may follow.

- **ioi**  
  - Inside – outside – inside sequence.  
  - Classic breakout mode pattern: market is coiling and may break sharply.

- **oo**  
  - Outside – outside sequence.  
  - High volatility; can mark a shift in state or a strong breakout zone.

- **Micro double top / bottom**  
  - Two nearby highs at almost the same price (or two lows).  
  - Local exhaustion signal or small-scale support/resistance.

- **Barbwire**  
  - Cluster of overlapping bars with many dojis and small bodies.  
  - Sign of confusion and poor reward-to-risk; best avoided.

These patterns gain meaning only when combined with context: trend direction, location within a range, time of day, etc.
