# Candidates tested

All numbers are Net PnL in USDC from a faithful local replay of the
harness (`agent-fun/bars-replay/v1` fill math: fee 10 bps + slippage
5 bps + constant-product impact against each bar's open depth, fills at
the next bar's open, flatten at the last close). Docker is not available
in this VM, so the kit's `grade-local --driver docker` could not run;
the replay was validated against the shipped baselines (buy-and-hold
reproduces exactly: -$869.34 on the full dev window) and re-implements
the decision checks, fill formulas and metrics from
`harness/harness-src.tar.gz` (`sim/bars/engine.ts`, `sim/metrics.ts`).

Buy-and-hold reference per window: full 136 bars -$869.34; first 72
-$686.14; middle 72 (bars 32–104) -$17.61; last 72 (bars 64–136)
-$311.77; first half (0–68) -$660.25; second half (68–136) -$247.19;
bull stretch bars 25–97 +$392.05; bull stretch bars 24–96 +$382.07.

Shipped house baselines, dev full / bull stretch (bars 25–97):
buy-and-hold -869.34 / +392.05; momentum -268.23 / -140.37; ema-cross
-173.04 / -76.11; adx-momentum -114.42 / -30.38; rsi-bollinger -56.49 /
-8.26; macd-cci -20.22 / -62.85. Note: every house baseline loses to
buy-and-hold in the bull stretch, while it wins in the downtrend — the
final window's regime decides which side of that trade matters.

## Round 1 — momentum rotation, no buy-at-open (12 candidates)

Lookback / top-N / rebalance / regime-min / stop. Net PnL on full 136
bars, then the three rolling 72-bar windows:

| Variant | Full | 72a | 72b | 72c | 2x fees (full) |
| --- | --- | --- | --- | --- | --- |
| mom12_top3_r12_stop6 | +157 | +185 | -154 | 0 | +122 |
| mom12_top4_r12_stop6 | +198 | +233 | -164 | 0 | +157 |
| mom12_top3_r12_nostop | +157 | +185 | -154 | 0 | +122 |
| mom12_top3_r12_reg05 | +157 | +185 | -51 | 0 | +122 |
| mom12_top3_r6_stop6 | -756 | -706 | -137 | -53 | -838 |
| mom24_top3_r12_stop6 | -196 | -193 | -95 | 0 | -215 |
| mom24_top3_r24_stop6 | -176 | -173 | -54 | 0 | -191 |
| mom6_top3_r6_stop6 | -475 | -425 | -286 | -97 | -560 |
| idx12_r12_stop6 (hold all 7) | +110 | +139 | +51 | 0 | +66 |
| idx24_r24_stop6 | -149 | -151 | -134 | 0 | -169 |

Lessons: rebalance every 6 bars churns fees to death (-756); lookback
24 is too slow (-196); stops (3/6/10% vs none) never fired — the
12-bar rebalance exit dominates. Momentum without buy-at-open loses to
buy-and-hold in the bull stretch (+254 vs +392) because of entry lag:
it enters at bar 12 and exits everything at bar 36 on one weak
12-bar index reading, missing the rest of the rally.

## Round 2 — filters on top of mom12_top4_r12

| Variant | Full | 72a | 72b | Bull 25–97 |
| --- | --- | --- | --- | --- |
| reg05 (regime > +0.5%) | +198 | +233 | -62 | +254 |
| reg10 (regime > +1.0%) | +198 | +233 | 0 | +254 |
| entry10 (enter only ret > +1%) | +198 | +233 | -74 | +254 |
| reg05 + entry10 | +198 | +233 | -36 | +254 |
| trail3 / trail5 | +198 | +233 | -151/-164 | +270/+254 |
| exitbar (exit if idx12 < -1% any bar) | -224 | -191 | -194 | -99 |
| regime2 (also need idx24 > 0) | -116 | -116 | -172 | -87 |
| top2 + reg05 | +56 | +72 | -36 | +95 |
| idx12 + reg05 | +110 | +139 | -25 | +179 |
| idx12 + trail3 | +110 | +139 | +45 | +188 |

Lessons: hysteresis/exitbar/regime2 all hurt — holding through weak
stretches rides declines; the plain regime gate at rebalance time is
the best exit. Top-4 beats top-2/top-3 on the full window.

## Round 3 — hysteresis and buy-at-open

| Variant | Full | 72a | 72b | Bull 25–97 |
| --- | --- | --- | --- | --- |
| mom4 + hysteresis (-1%) | -213 | +194 | -249 | +205 |
| mom4 + hysteresis + buy-at-open | -511 | -119 | -170 | +332 |
| mom4 + buy-at-open only | -114 | -81 | -36 | +414 |
| idx12 + hysteresis + buy-at-open | -575 | -189 | +1 | +317 |
| mom4 + hysteresis, R24 | -467 | -185 | -102 | -142 |

Lesson: hysteresis is bad (see round 2). Buy-at-open alone is the
breakthrough: it is the first variant to beat buy-and-hold in the bull
stretch (+414 vs +392) because it matches buy-and-hold's entry and
then adds rotation + regime exits on top.

## Round 4 — refining buy-at-open (base: L12, top4, R12, reg05, trail3)

| Variant | Full | 72a | 72b | Bull 25–97 | 2x fees |
| --- | --- | --- | --- | --- | --- |
| open (reg05) | -114 | -81 | -36 | +414 | -173 |
| open + reg10 | -114 | -81 | +26 | +414 | -173 |
| open + reg10 + trail5 | -115 | -81 | +26 | +420 | -174 |
| open + notrail | -92 | -59 | -36 | +420 | -151 |
| open + entry10 | -114 | -81 | -10 | +414 | -173 |
| open + top3 / top2 | -154/-252 | -127/-237 | -25/-10 | +415/+415 | -208/-296 |
| open + R24 | -670 | -669 | +107 | +404 | -707 |
| open + breaker (-2% / -3% on 6-bar idx) | -178 | -145 | -36 | +414 | -237 |
| open + L24 | -681 | -680 | +38 | +374 | -723 |

Lessons: rebalance 24 and lookback 24 are far too slow once the bot
starts invested (it rides the opening decline). The breaker fires on
noise and costs money. Regime +1.0% fixes the flat window (72b -36 →
+26) at no cost elsewhere.

## Round 5 — finalists (all buy-at-open, L12, top4, R12)

| Variant | Full | 72a | 72b | 72c | Bull 25–97 | Bull 24–96 | 2x fees |
| --- | --- | --- | --- | --- | --- | --- | --- |
| reg10 + trail5 | -115 | -81 | +26 | -86 | +420 | +438 | -174 |
| reg10 + notrail | -92 | -59 | +26 | -86 | +420 | +438 | -151 |
| reg10 + entry10 | -115 | -81 | +26 | -86 | +420 | +438 | -174 |
| reg15 + trail5 | -81 | -81 | +26 | -86 | +420 | +438 | -121 |
| reg10 + top3 | -154 | -127 | +26 | -86 | +359 | +411 | -208 |

Synthetic slow-grind windows (dev bull stretch with log-returns
scaled ×0.5 / ×0.25; buy-and-hold +141.73 / +19.50 there):

| Variant | Grind ×0.5 | Grind ×0.25 | Bear ×0.5 (full) |
| --- | --- | --- | --- |
| reg05 (round 3) | +185 (+43 vs B&H) | +70 (+50) | -132 (+342) |
| reg10 + trail5/notrail | +185 (+43) | +26 (+6) | -78 (+395) |
| reg15 + trail5 | +96 (-46) | +26 (+6) | -165 (+308) |
| mom4 reg05, no open | +99 (-43) | +22 (+2) | +45 (+518) |

## Decision

**Picked: reg10 + notrail** — LOOKBACK 12, TOP_N 4, REBALANCE 12,
REGIME_MIN +1.0%, ENTRY_MIN 0, STOP_PCT 0, TRAIL_PCT 0,
BUY_AT_OPEN. It beats buy-and-hold in all 11 windows tested (6 real
+ 2 bull stretches + 3 synthetic), including both bull stretches
(+$28 / +$56) and both grind windows (+$43 / +$6), with max drawdown
4.02% on the full window (cap 25%) and 26 trades (min 8). The
trailing stop was dropped because it only ever cost money in testing
(full -115 vs -92, 2x fees -174 vs -151, identical everywhere else);
the 12-bar regime exit is the live risk control. Regime +1.5% was
rejected despite the best full-window score (-81, 2x -121) because it
loses to buy-and-hold in the half-speed grind (+96 vs +142) — a slow
final rally would leave it in cash.

## Open risks (honest)

- The bull-stretch margin is thin (+$28–56 on $10,000). If the final
  window is a strong, steady rally, buy-and-hold is hard to beat and
  the margin could flip on noise; if it is a downtrend or chop, this
  entry wins by a wide margin.
- No variant beats buy-and-hold by a lot in a bull market — the edge
  there is entry timing (zero lag) plus rotation into the strongest
  names, worth ~1% of the rally.
- The house baselines all score below buy-and-hold in the bull
  stretch, so in a bull final this entry plausibly ranks above them;
  in a bear final the no-open momentum variant (+198 dev) would rank
  above this one, but this one still beats buy-and-hold by ~+$780 on
  the full dev window and would still place.
- The final window's prices do not exist yet; every number above is
  dev-window evidence only.
