# Pattern Glossary for Feature Fields

This document maps numeric feature fields to price action concepts.

## 1. Regime and Environment

- **trending_score (0–1)**  
  - 0 = clearly not trending, 1 = strong trend environment.  
- **ranging_score (0–1)**  
  - 0 = clearly not ranging, 1 = strong trading range environment.  
- **reversal_setup_score (0–1)**  
  - 0 = no obvious reversal setup, 1 = strong signs of a major reversal pattern.  
- **breakout_mode_score (0–1)**  
  - 0 = no compression, 1 = market tightly coiled, ready for breakout.

## 2. Bar-Level Fields

- **body_rel (0–1)**  
  - Body size as a fraction of total bar range. Large ≈ strong trend bar.  
- **upper_tail_rel / lower_tail_rel (0–1)**  
  - Proportion of wick on each side; large tails can signal rejection.  
- **close_pos_rel (0–1)**  
  - Close location within bar:  
    - ≈ 0 → near low,  
    - ≈ 0.5 → mid,  
    - ≈ 1 → near high.  
- **range_rel_atr**  
  - Bar range divided by ATR; >1 means larger than recent typical range.  
- **is_trend_bar_score (0–1)**  
  - Confidence that the bar is a strong trend bar.  
- **is_doji_score (0–1)**  
  - Confidence that the bar is a doji / indecision bar.  
- **is_outside_score / is_inside_score (0–1)**  
  - Likelihood the bar is an outside or inside bar.  
- **volume_zscore**  
  - Positive values = higher than typical volume; negative = lower.

## 3. Local Trend Fields

- **ema_slope**  
  - Normalized slope of the EMA; sign shows trend direction.  
- **bars_above_ema_ratio (0–1)**  
  - Fraction of recent bars above EMA; high in bull trends, low in bear trends.  
- **consecutive_bull_bars / consecutive_bear_bars**  
  - Count of same-direction bars in a row.  
- **micro_channel_bars**  
  - Length of recent micro channel (sequence with little/no pullback).  
- **pullback_depth_rel**  
  - Depth of the latest pullback relative to the prior trend leg.  
- **pullback_bars**  
  - Number of bars in the latest pullback.  
- **spike_strength (0–1)**  
  - Strength of recent spike.  
- **trend_persistence (0–1)**  
  - How consistently one side has dominated recently.

## 4. Swing Structure

- **swing_direction**  
  - +1 = last swing up, -1 = last swing down, 0 = unclear.  
- **hh_ll_score (0–1)**  
  - Strength of higher-high/higher-low or lower-high/lower-low structure.  
- **swing_leg1_size / swing_leg2_size**  
  - Sizes of the last two legs in ATR units.  
- **leg2_vs_leg1_ratio**  
  - Ratio of second leg to first; >1 suggests acceleration.  
- **wedge_push_count**  
  - Number of pushes in the current direction (1, 2, or 3+).  
- **wedge_score (0–1)**  
  - Likelihood that the structure is a wedge.  
- **double_top_score / double_bottom_score (0–1)**  
  - Likelihood of a double top or double bottom pattern.

## 5. Range Structure

- **overlap_ratio (0–1)**  
  - Degree of bar overlap; high implies a range.  
- **range_height_rel_atr**  
  - Range height vs ATR.  
- **time_in_range_bars**  
  - Number of bars spent within the current range.  
- **tests_of_range_high / tests_of_range_low**  
  - Count of tests at range boundaries.  
- **breakout_attempts**  
  - Number of recent attempts to break out of the range.  
- **breakout_fail_ratio (0–1)**  
  - Fraction of breakout attempts that failed.  
- **barbwire_score (0–1)**  
  - How much the structure resembles noisy overlapping barbwire.

## 6. Reversal Signals

- **trendline_break_score (0–1)**  
  - Likelihood of a recent break of a trend line.  
- **channel_overshoot_score (0–1)**  
  - Degree to which price overshot a channel line.  
- **climax_runup_score (0–1)**  
  - Strength of recent climactic move.  
- **pullback_after_climax_bars**  
  - Number of bars in the pullback after a climax.  
- **higher_low_score / lower_high_score (0–1)**  
  - Strength of HL/LH structure indicating potential reversal.  
- **high1_score / high2_score / low1_score / low2_score (0–1)**  
  - Strength of H1/H2/L1/L2 signal patterns.  
- **final_flag_score (0–1)**  
  - Likelihood that the recent flag is a “final flag” before reversal.

## 7. Risk and Reward Metrics

- **nearest_support_dist / nearest_resistance_dist**  
  - Distance to nearest support/resistance (in points or ATR units).  
- **stop_distance_suggested**  
  - Typical protective stop distance in ATR units.  
- **scalp_target_dist / swing_target_dist**  
  - Typical scalp and swing target distances (ATR units).  
- **rr_swing_estimate / rr_scalp_estimate**  
  - Estimated reward-to-risk for swing and scalp trades.  
- **prob_trend_continuation / prob_reversal / prob_range_continuation (0–1)**  
  - Rough probabilities for each scenario, based on quantitative features.

These fields are the bridge between numeric feature engineering and Brooks-style qualitative reasoning.
