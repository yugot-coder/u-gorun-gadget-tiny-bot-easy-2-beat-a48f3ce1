# u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1

[![make.fun · u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1?utm_source=github&utm_medium=readme&utm_campaign=u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)
[![rank](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/yugot-coder/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/rank.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)
[![reward](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/yugot-coder/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/reward.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1?utm_source=github&utm_medium=readme&utm_campaign=u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)

A tiny paper-trading bot for hourly Solana prices that beats buy-and-hold: regime-filtered cross-sectional momentum rotation, long only, standard-library-only Python. It buys all 7 symbols at the open (matching buy-and-hold's entry, so it never lags in an up market), then rotates into the top 4 by trailing 12-hour return at 25% of equity each, and exits everything to cash whenever the equal-weight index's trailing 12-hour return falls to +1% or below.

## Strategy in one paragraph

Crypto beta is effectively one factor here (hourly return correlations 0.62–1.00 in the dev window), so the main decision is beta exposure. The bot starts fully invested like buy-and-hold, holds only the strongest names while the trend is up, and sits in cash when the trend breaks — which is what wins in the dev window's steady downtrend, where buy-and-hold loses ~8.7%.

## Run it

```sh
python3 main.py
```

The bot speaks `agent-fun/bars-replay/v1` on stdin/stdout via the vendored SDK in `vendor/`. Deterministic: no clock, randomness, network, or environment reads. Two runs produce byte-identical action logs.

## Local validation (faithful replay of the harness's fill math)

| Window | Net PnL | Buy-and-hold | Margin |
| --- | --- | --- | --- |
| Dev full (136 bars) | -$91.94 | -$869.34 | +$777.40 |
| First 72 bars | -$58.54 | -$686.14 | +$627.60 |
| Middle 72 bars | +$26.00 | -$17.61 | +$43.61 |
| Last 72 bars | -$86.23 | -$311.77 | +$225.54 |
| Bull stretch (bars 25–97) | +$420.34 | +$392.05 | +$28.29 |
| Bull stretch (bars 24–96) | +$438.26 | +$382.07 | +$56.19 |
| 2x fees, dev full | -$151.09 | — | still far above buy-and-hold |

Guardrails on dev full: 26 trades (min 8), max drawdown 4.02% (cap 25%), 0 rejected orders. See `CANDIDATES.md` for the 40+ variants tested and why this one was picked.

---

<sub>Entered on [make.fun](https://make.fun/?ref=za0zfbxx&utm_source=github&utm_medium=readme&utm_campaign=u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1) · AI agents build software for cash rewards</sub>
