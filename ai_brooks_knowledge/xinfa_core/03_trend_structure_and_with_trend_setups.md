# Trend Structure and With-Trend Setups

This document describes how to read and trade trends using the feature snapshot.

## 1. Recognizing Bull and Bear Trends

A **bull trend** usually shows:

- Series of higher highs and higher lows.  
- Most bars trading above a rising EMA.  
- Pullbacks are small in depth and duration.  
- Frequent bull trend bars; strong closes near bar highs.

A **bear trend** is the mirror image.

In the features:

- `ema_slope > 0` and `bars_above_ema_ratio` high → bull tendency.  
- `ema_slope < 0` and `bars_above_ema_ratio` low → bear tendency.  
- `trend_persistence` measures how consistently one side has controlled recent bars.

## 2. Spike and Channel

Trends are often “spike and channel”:

- **Spike** – a sudden strong move with multiple large trend bars and little overlap.  
- **Channel** – a more gradual move with pullbacks but still overall directional.

In features:

- High `spike_strength` marks the spike phase.  
- Later, `micro_channel_bars` and moderate overlaps represent the channel phase.

## 3. Pullbacks and H1 / H2 / L1 / L2

- In a bull trend:  
  - A downward correction is a pullback.  
  - **High 1 (H1)**: first bar whose high breaks above the prior bar’s high during the pullback.  
  - **High 2 (H2)**: second attempt to resume the bull trend after a deeper or longer pullback.  
- In a bear trend:  
  - **Low 1 (L1)** and **Low 2 (L2)** are the analogs.

In features:

- `high1_score`, `high2_score`, `low1_score`, `low2_score` express the strength/clarity of these signals.

General rule:

- H1/L1 can work in a strong trend, but H2/L2 are usually more reliable, especially after a deep or complex pullback.

## 4. With-Trend Entries

Common with-trend entries:

1. **Pullback to EMA or prior support/resistance**  
   - Enter in the trend direction when price tests the EMA, a prior swing high/low, or the top/bottom of a prior micro range.

2. **Pullback after breakout**  
   - Strong breakout from a range or pattern → wait for a small pullback that holds above/below the breakout level, then enter in the breakout direction.

3. **Small pullback trend**  
   - In very strong trends, pullbacks are only 1–3 bars and very shallow.  
   - Enter on small pullbacks but avoid chasing late in an extended, climactic channel.

The agent should favor with-trend entries when:

- `trending_score` is high,  
- `prob_trend_continuation > prob_reversal`,  
- pullback depth and duration are normal (not extremely late or extremely deep).
