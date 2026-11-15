"""BTC race bot — capitulation-bounce sniper (long only, one setup).

The idea: BTC occasionally capitulates — a violent multi-hour drop that ends
in a long lower wick and a sharp reversal bar. This bot sits in cash, waits
for exactly that shape, buys it at full size, and rides the bounce with a
trailing stop. It trades nothing else. Momentum longs on 1-minute bars were
removed: held-out testing showed they lose (0 wins in 7 trades).

Entry (all of these, drop measured on the bar BEFORE the reversal bar):
  1. The close fell >= 150 bps over 60 bars, or >= 250 bps over 120 bars.
  2. The close fell >= 550 bps from the highest high of the last 720 bars.
  3. A long-lower-wick bar (range >= 20 bps, close in the top 40% of its
     range) appeared in the last 20 bars.
  4. The current bar closed up >= 60 bps on the previous close and above
     the previous bar's high (the reversal).
  5. RSI(14) is turning up.
  6. Reward-to-risk: the distance back up to the 720-bar high is at least
     twice the distance down to the stop.

Exit: a stop below the capitulation low (clamped to 50-100 bps under the
entry), a trailing stop that arms once price is +80 bps and then trails the
peak close by 80 bps, or a 300-bar maximum hold.

Guards: at most 2 entries per window, stop after 2 consecutive losses, never
enter below 98% of starting equity, no entries after bar 1320, and a 60-bar
cooldown after any exit.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
BPS = 10_000

# --- entry thresholds (basis points) -------------------------------------
NEED_DROP_60 = 150       # drop over 60 bars
NEED_DROP_120 = 250      # drop over 120 bars
NEED_DROP_HIGH = 550     # drop from the 720-bar high
WICK_RANGE = 20          # wick bar range, in bps of its close
WICK_TOP = 60            # close must sit at/above 60% of the wick bar range
REVERSAL_UP = 60         # reversal bar must close up this many bps
MIN_RR = 2               # reward must be >= 2x the risk

# --- exits ----------------------------------------------------------------
STOP_FLOOR_BPS = 50      # stop never closer than this under the entry
STOP_CEIL_BPS = 100      # stop never further than this under the entry
TRAIL_ARM_BPS = 80       # trailing stop arms once price is this far above entry
TRAIL_GAP_BPS = 80       # trailing stop trails the peak close by this much
MAX_HOLD = 300           # bars

# --- guards ---------------------------------------------------------------
MAX_ENTRIES = 2
MAX_LOSERS = 2
EQUITY_FLOOR_BPS = 9_800  # 98% of starting equity
LAST_ENTRY_BAR = 1_320
COOLDOWN = 60
SLIP_BPS = 500           # max slippage on any order (fills are ~1 bar away)
RSI_LEN = 14
LOOKBACK_HIGH = 720
LOOKBACK_WICK = 20


def _rsi(closes, period, upto):
    """Wilder's RSI(period) of closes[0..upto]. None when not enough data."""
    if upto < period:
        return None
    gain = 0.0
    loss = 0.0
    for k in range(1, period + 1):
        move = closes[k] - closes[k - 1]
        if move > 0:
            gain += move
        else:
            loss -= move
    avg_gain = gain / period
    avg_loss = loss / period
    for k in range(period + 1, upto + 1):
        move = closes[k] - closes[k - 1]
        up = move if move > 0 else 0
        down = -move if move < 0 else 0
        avg_gain = (avg_gain * (period - 1) + up) / period
        avg_loss = (avg_loss * (period - 1) + down) / period
    if avg_loss == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


class Sniper:
    """One window of state: the bar tape and the open trade, if any."""

    def __init__(self):
        self.closes = []
        self.highs = []
        self.lows = []
        self.start_equity = None
        self.entries = 0
        self.losers = 0
        self.cool_until = -1
        # open-trade bookkeeping (decision-bar reference prices)
        self.entry_ref = None
        self.entry_bar = None
        self.stop = None
        self.trail = None
        self.armed = False
        self.peak = None

    def _drop_bps(self, end_idx, span):
        """Close-to-close drop over `span` bars ending at end_idx, in bps
        (negative when the price fell)."""
        ref = self.closes[end_idx - span]
        return (self.closes[end_idx] - ref) * BPS // ref

    def _setup(self, i):
        """True when bar i is a capitulation-bounce entry. Drops are read off
        bar i-1, because the reversal bar itself lifts the close."""
        prev = i - 1
        if prev < LOOKBACK_HIGH:
            return False
        # 1) a sharp drop just happened
        fell_fast = (
            self._drop_bps(prev, 60) <= -NEED_DROP_60
            or self._drop_bps(prev, 120) <= -NEED_DROP_120
        )
        if not fell_fast:
            return False
        # 2) it fell a long way from the 12-hour high
        high720 = max(self.highs[prev - LOOKBACK_HIGH + 1: prev + 1])
        drop_high = (self.closes[prev] - high720) * BPS // high720
        if drop_high > -NEED_DROP_HIGH:
            return False
        # 3) a long lower wick printed in the last 20 bars
        wick = False
        for j in range(max(0, i - LOOKBACK_WICK), i):
            rng = self.highs[j] - self.lows[j]
            if rng <= 0:
                continue
            if rng * BPS // self.closes[j] < WICK_RANGE:
                continue
            if (self.closes[j] - self.lows[j]) * 100 // rng >= WICK_TOP:
                wick = True
                break
        if not wick:
            return False
        # 4) this bar is the reversal: up sharply and above the prior high
        if self.closes[i] < self.closes[prev] * (BPS + REVERSAL_UP) // BPS:
            return False
        if self.closes[i] <= self.highs[prev]:
            return False
        # 5) RSI is turning up
        rsi_now = _rsi(self.closes, RSI_LEN, i)
        rsi_prev = _rsi(self.closes, RSI_LEN, prev)
        if rsi_now is None or rsi_prev is None or rsi_now <= rsi_prev:
            return False
        # 6) reward-to-risk: room back to the 720-bar high >= 2x the stop
        cap_low = min(self.lows[prev - LOOKBACK_HIGH + 1: prev + 1])
        ref = self.closes[i]
        stop_lowest = ref * (BPS - STOP_CEIL_BPS) // BPS
        stop_highest = ref * (BPS - STOP_FLOOR_BPS) // BPS
        stop = cap_low
        if stop < stop_lowest:
            stop = stop_lowest
        if stop > stop_highest:
            stop = stop_highest
        risk = ref - stop
        if risk <= 0:
            return False
        if high720 - ref < MIN_RR * risk:
            return False
        self._pending_stop = stop
        return True

    def on_batch(self, state, batch):
        bar = state.latest.get(SYMBOL)
        if bar is None:
            return []
        self.closes.append(int(bar["c"]))
        self.highs.append(int(bar["h"]))
        self.lows.append(int(bar["l"]))
        i = state.seq
        if self.start_equity is None:
            self.start_equity = state.equity
        if state.warming_up:
            return []

        holding = state.positions.get(SYMBOL)
        if holding is not None:
            return self._manage(state, i, holding)
        return self._maybe_enter(state, i)

    def _manage(self, state, i, holding):
        """We hold a position: trail the stop, or get out."""
        close = self.closes[i]
        if self.peak is None or close > self.peak:
            self.peak = close
        # arm the trailing stop once price is far enough above the entry
        if not self.armed and self.entry_ref is not None:
            if close >= self.entry_ref * (BPS + TRAIL_ARM_BPS) // BPS:
                self.armed = True
        if self.armed:
            trail = self.peak * (BPS - TRAIL_GAP_BPS) // BPS
            if self.trail is None or trail > self.trail:
                self.trail = trail
        # exit: stop hit, trailing stop hit, or held too long
        stop_hit = self.stop is not None and close < self.stop
        trail_hit = self.armed and self.trail is not None and close < self.trail
        too_long = self.entry_bar is not None and i - self.entry_bar >= MAX_HOLD
        if stop_hit or trail_hit or too_long:
            if self.entry_ref is not None and close < self.entry_ref:
                self.losers += 1
            else:
                self.losers = 0
            self.cool_until = i + COOLDOWN
            self.entry_ref = None
            self.entry_bar = None
            self.stop = None
            self.trail = None
            self.armed = False
            self.peak = None
            return [{
                "side": "sell",
                "symbol": SYMBOL,
                "qty": holding.qty,
                "max_slippage_bps": SLIP_BPS,
            }]
        return []

    def _maybe_enter(self, state, i):
        """Flat: enter only when the setup and every guard agree."""
        if self.entries >= MAX_ENTRIES:
            return []
        if self.losers >= MAX_LOSERS:
            return []
        if i > LAST_ENTRY_BAR:
            return []
        if i < self.cool_until:
            return []
        if self.start_equity and state.equity * BPS // self.start_equity < EQUITY_FLOOR_BPS:
            return []
        if state.cash < 1_000_000:
            return []
        self._pending_stop = None
        if not self._setup(i):
            return []
        self.entries += 1
        self.entry_ref = self.closes[i]
        self.entry_bar = i
        self.stop = self._pending_stop
        self.trail = None
        self.armed = False
        self.peak = self.closes[i]
        return [{
            "side": "buy",
            "symbol": SYMBOL,
            "notional_quote_units": state.cash,
            "max_slippage_bps": SLIP_BPS,
        }]


_BOT = Sniper()


def on_batch(state, batch):
    return _BOT.on_batch(state, batch)


if __name__ == "__main__":
    makefun_bars.run(on_batch)
