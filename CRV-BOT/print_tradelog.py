"""Print full trade log from the latest backtest run."""
import backtest
import pandas as pd
import builtins

def dummy_print(*args, **kwargs):
    pass
orig_print = builtins.print

orig_print("Fetching data and running backtest (SL=20%, CB=50%, Cooldown=6)...")
builtins.print = dummy_print
df_raw = backtest.fetch_ohlcv_1y()
df_ind = backtest.compute_indicators(df_raw)
df_res, trades, sig_l, sig_s, sig_sl, sig_cb = backtest.run_backtest(df_ind)
builtins.print = orig_print

lines = []
lines.append("=" * 130)
lines.append("  FULL TRADE LOG - CRV/USDT Mean Reversion Bot (SL=20% | CB=50% | Cooldown=24h)")
lines.append("=" * 130)
lines.append(f"  {'#':>3} {'Dir':6} {'Entry Date':<16} {'Exit Date':<16} {'Entry':>8} {'Exit':>8} {'PnL ($)':>12} {'PnL %':>8} {'Reason':16} {'Dur':>6} {'Eq After':>14}")
lines.append(f"  {'---':>3} {'------':6} {'----------------':<16} {'----------------':<16} {'--------':>8} {'--------':>8} {'------------':>12} {'--------':>8} {'----------------':16} {'------':>6} {'--------------':>14}")

for idx, t in enumerate(trades, start=1):
    dur = (pd.to_datetime(t["exit_time"]) - pd.to_datetime(t["entry_time"]))
    dur_h = dur.total_seconds() / 3600
    entry_dt = pd.to_datetime(t["entry_time"]).strftime("%Y-%m-%d %H:%M")
    exit_dt = pd.to_datetime(t["exit_time"]).strftime("%Y-%m-%d %H:%M")
    lines.append(f"  {idx:>3} {t['direction']:6} {entry_dt:<16} {exit_dt:<16} {t['entry_price']:>8.4f} {t['exit_price']:>8.4f} ${t['pnl_usdt']:>+11.2f} {t['pnl_pct']:>+7.2f}% {t['exit_reason']:16} {dur_h:>5.0f}h ${t['equity_after']:>13,.2f}")

wins = sum(1 for t in trades if t['pnl_usdt'] > 0)
losses = sum(1 for t in trades if t['pnl_usdt'] <= 0)
lines.append(f"\n  Total: {len(trades)} | Wins: {wins} | Losses: {losses} | Win Rate: {wins/len(trades)*100:.1f}%")
lines.append(f"  Final Equity: ${trades[-1]['equity_after']:,.2f}")

with open("full_tradelog.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

orig_print("Trade log saved to full_tradelog.txt")
