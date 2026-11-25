"""Tiny Bot: regime-filtered cross-sectional momentum rotation (long only).

Competition: u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1
("Tiny Bot, Easy $2: Beat Buy-and-Hold on Solana").
Harness: agent-fun/bars-replay/v1, $10,000 USDC, 7 Solana symbols, 1h bars,
fee 10 bps + slippage 5 bps, max 25% weight per position, no shorts, no
leverage. Final window is 72 hourly bars (27-30 Nov 2026) whose prices do
not exist yet, so the strategy is built for robustness across regimes,
not for fitting the dev window.

Why this shape: in the dev window the 7 symbols' hourly returns correlate
0.62-1.00, so crypto beta is effectively one factor and the main decision
is beta exposure, not stock-picking. The dev window is a steady downtrend
in which buy-and-hold loses ~8.7%, so cash is the winning move there --
but the final window could be up, down or flat, and the prize needs a Net
PnL above buy-and-hold in whichever regime shows up.

Rules (all deterministic, float arithmetic on closes only):
  1. Buy-at-open: on the first batch, buy an equal slice of all 7 symbols
     (~14.3% of equity each). This matches buy-and-hold's entry exactly,
     so in an up market the bot is never behind on entry lag -- the lag
     is what made every no-open momentum variant lose to buy-and-hold
     in the dev window's bull stretch.
  2. Regime filter: at every 12-bar rebalance, compute the equal-weight
     index's trailing 12-bar return. If it is at or under REGIME_MIN
     (+1.0%), exit everything to cash; if above it, stay invested. The
     +1.0% bar (not 0%) keeps the bot out of flat/choppy stretches where
     re-entries only pay fees.
  3. Rotation: while invested, hold the TOP_N = 4 symbols by trailing
     12-bar return, 25% of equity each (the weight cap), rebalanced every
     12 bars. Buys are deferred one bar after a reply that sells, because
     a sell's proceeds never fund a buy in the same reply.
  4. Risk controls: a fixed stop (STOP_PCT) and a trailing stop
     (TRAIL_PCT) are implemented and checked every bar, but both are set
     to 0 (off) in this entry: in testing across the dev window, its
     sub-windows and synthetic grind windows, the 12-bar regime exit
     alone kept max drawdown at ~4% (cap 25%) and both stops only ever
     cost money through whipsaws. Max slippage is 1000 bps (10%) so a
     fill is refused rather than filled through a liquidity gap.

What was tested (local replay faithful to the harness's fill math, see
CANDIDATES.md): 40+ variants over the full 136-bar dev window, three
rolling 72-bar windows, two halves, the dev window's bull stretch
(bars 25-97), and synthetic half/quarter-speed grind windows. This
variant beats buy-and-hold in every one of those windows.

Dev-window result (local replay, 1x fees): Net PnL -$91.94 vs
buy-and-hold -$869.34 (margin +$777.40), 26 trades, max drawdown 4.02%,
fees $59.25. At 2x fees: -$151.09, still far above buy-and-hold.
Walk-forward margins over buy-and-hold: first 72 bars +$627.60,
middle 72 +$43.61, last 72 +$225.54, bull stretch bars 25-97 +$28.29,
bars 24-96 +$56.19, half-speed grind +$43, quarter-speed grind +$6,
half-speed bear +$395 — above buy-and-hold in every window tested.
Deterministic: two runs produce byte-identical action logs.

Protocol: agent-fun/bars-replay/v1 via the vendored SDK (stdlib only).
The grader runs `python3 -P -s main.py`; the vendor directory is put on
sys.path explicitly because -P leaves the script's directory off it.
No clock, no randomness, no network, no environment reads.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

LOOKBACK = 12
TOP_N = 4
REBALANCE = 12
REGIME_MIN = 0.01
ENTRY_MIN = 0.0
STOP_PCT = 0.0
TRAIL_PCT = 0.0
MAX_SLIP = 1000

# closes[symbol] = list of latest closes by seq (int, or None before first bar)
closes = {}
pending_buys = None
peaks = {}


def _ret(sym, seq, lb):
    """Trailing lb-bar return of sym at seq, or None without the history."""
    hist = closes.get(sym)
    if hist is None or seq < lb:
        return None
    now = hist[seq]
    then = hist[seq - lb]
    if now is None or then is None or then == 0:
        return None
    return now / then - 1.0


def _index_ret(state, seq, lb):
    """Equal-weight index trailing return over lb bars, or None."""
    vals = []
    for s in state.hello["symbols"]:
        r = _ret(s["symbol"], seq, lb)
        if r is not None:
            vals.append(r)
    if not vals:
        return None
    return sum(vals) / len(vals)


def _buys(state, symbols):
    """Equal slices for symbols not already held, capped at 25% of equity."""
    coming = [s for s in symbols if s not in state.positions and state.close(s) is not None]
    if not coming:
        return []
    orders = []
    cash = state.cash
    even = cash // len(coming)
    for sym in coming:
        room = state.weight_room(sym)
        slice_ = even if even <= room else room
        if slice_ < int(state.hello["fees"]["min_notional_quote_units"]):
            continue
        orders.append({"side": "buy", "symbol": sym,
                       "notional_quote_units": slice_, "max_slippage_bps": MAX_SLIP})
        cash -= slice_
    return orders


def _target(state, seq):
    """Symbols to hold at this rebalance, best first (momentum order)."""
    rets = {}
    for s in state.hello["symbols"]:
        r = _ret(s["symbol"], seq, LOOKBACK)
        if r is not None:
            rets[s["symbol"]] = r
    if not rets:
        return []
    if _index_ret(state, seq, LOOKBACK) <= REGIME_MIN:
        return []
    ranked = sorted(rets, key=lambda s: (-rets[s], s))
    return [s for s in ranked[:TOP_N] if rets[s] > ENTRY_MIN]


def on_batch(state, batch):
    global pending_buys
    seq = batch["seq"]
    for bar in batch["bars"]:
        closes.setdefault(bar["symbol"], []).append(
            int(bar["c"]) if bar["c"] is not None else None)
    if state.warming_up:
        return []
    # Track each held position's peak value (at the close) for the trailing stop.
    for sym, held in state.positions.items():
        val = state.value(sym, held.qty)
        if sym not in peaks or val > peaks[sym]:
            peaks[sym] = val
    orders = []
    # 1. Every-bar exits: fixed stop and trailing stop (both off at 0.0
    #    in this entry; the 12-bar regime exit below is the live control).
    for sym, held in sorted(state.positions.items()):
        val = state.value(sym, held.qty)
        stop_hit = STOP_PCT > 0 and val < held.cost * (1.0 - STOP_PCT)
        trail_hit = TRAIL_PCT > 0 and sym in peaks and val < peaks[sym] * (1.0 - TRAIL_PCT)
        if stop_hit or trail_hit:
            orders.append({"side": "sell", "symbol": sym, "qty": held.qty,
                           "max_slippage_bps": MAX_SLIP})
            peaks.pop(sym, None)
    if orders:
        pending_buys = None
        return orders
    # 2. Buys deferred from the previous bar's rebalance sells.
    if pending_buys is not None:
        want = pending_buys
        pending_buys = None
        return _buys(state, want)
    # 2b. Buy-at-open: match buy-and-hold's entry (no lookback lag), then
    # let rotation / the regime filter take over from the first rebalance.
    if seq == 0:
        return _buys(state, [s["symbol"] for s in state.hello["symbols"]])
    # 3. Rebalance every REBALANCE bars.
    if seq >= LOOKBACK and seq % REBALANCE == 0:
        want = _target(state, seq)
        sells = [{"side": "sell", "symbol": sym, "qty": held.qty,
                  "max_slippage_bps": MAX_SLIP}
                 for sym, held in sorted(state.positions.items()) if sym not in want]
        if sells:
            for s in sells:
                peaks.pop(s["symbol"], None)
            pending_buys = [s for s in want if s not in state.positions]
            return sells
        return _buys(state, want)
    return []


makefun_bars.run(on_batch)
