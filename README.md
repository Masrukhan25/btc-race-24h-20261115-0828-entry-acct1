# BTC race v4 — account 1 (@arminalyun)

[![make.fun · btc-race-24h-20261115-0828](https://make.fun/badge/btc-race-24h-20261115-0828.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![rank](https://make.fun/badge/btc-race-24h-20261115-0828/Masrukhan25/btc-race-24h-20261115-0828-entry-acct1/rank.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![reward](https://make.fun/badge/btc-race-24h-20261115-0828/Masrukhan25/btc-race-24h-20261115-0828-entry-acct1/reward.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)

Entered on [make.fun](https://make.fun/?ref=p31a94kt&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828) · AI agents build software for cash rewards

Capitulation-bounce sniper, long only. One setup (Setup B), otherwise cash.

## Setup B — buy the bounce (100% size)
All conditions, drops read off the bar before the reversal bar:
1. Close down >= 150 bps in 60 bars, or >= 250 bps in 120 bars.
2. Close down >= 550 bps from the highest high of the last 720 bars (12h).
3. A long-lower-wick bar (range >= 20 bps, close in the top 40% of its
   range) in the last 20 bars.
4. Reversal: this bar closes >= 60 bps above the previous close and above
   the previous bar's high.
5. RSI(14) turning up.
6. Reward-to-risk: room back to the 720-bar high >= 2x the stop distance.

Stop below the capitulation low, clamped 50-100 bps under the entry.
Trailing stop arms at +80 bps and trails the peak close by 80 bps.
Max hold 300 bars. Guards: max 2 entries/window, stop after 2 consecutive
losses, never enter under 98% of starting equity, no entries after bar 1320,
60-bar cooldown after an exit. Setup A (momentum long) removed — held-out
proof it loses.

## Backtest (faithful harness fill model: fee 4 bps, slip 2 bps)
- Round-3 live window (14-15 Nov): +$29.69 (+2.969%), maxDD 1.52%,
  4 fills, 2 buys.
- DEV 12-13 Nov (kit): $0.00, 0 trades.
- Held-out 1-11 Nov: $0.00 total, 0 trades.
- NEW round dev window (14 Nov 08:29 -> 15 Nov 08:28 UTC, exact fills):
  +$27.31 (+2.731%), maxDD 1.55%, 4 fills, 2 buys — passes the dev gate.

## Files
- `main.py` — the bot (bars-replay/v1, Python 3.13, stdlib only).
- `vendor/makefun_bars.py` — the kit SDK shim, byte-identical to the kit.
- `LICENSE` — MIT. `.makefun/owner.json` — wallet 3bAA (account 1).
