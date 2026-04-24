"""
optimize_rsi_detailed.py
Grid Search RSI Oversold (25-35) x Overbought (65-75)
+  Analisis terpisah: Long-only vs Short-only per threshold
"""
import backtest
import builtins
import pandas as pd
import itertools
import numpy as np

def dummy_print(*args, **kwargs):
    pass

orig_print = builtins.print

# --- Fetch data sekali saja ---
orig_print("Fetching data...")
builtins.print = dummy_print
df_raw = backtest.fetch_ohlcv_1y()
df_ind  = backtest.compute_indicators(df_raw)
builtins.print = orig_print
orig_print(f"Data OK: {len(df_ind)} candles\n")

# --- Parameter tetap ---
backtest.STOP_LOSS_PCT      = 0.20
backtest.CIRCUIT_BREAKER_DD = 0.50
backtest.COOLDOWN_CANDLES   = 6
backtest.POSITION_SIZE_PCT  = 0.92
backtest.LEVERAGE           = 2

# =============================================================
# HELPER: Extract per-side stats from trades
# =============================================================
def get_side_stats(trades, side):
    """Extract win rate, avg pnl, count for LONG or SHORT only."""
    t = [x for x in trades if x["direction"] == side]
    if not t:
        return {"count": 0, "win_rate": 0, "avg_pnl": 0, "total_pnl": 0,
                "avg_pct": 0, "wins": 0, "losses": 0}
    wins   = [x for x in t if x["pnl_usdt"] > 0]
    losses = [x for x in t if x["pnl_usdt"] <= 0]
    return {
        "count"    : len(t),
        "wins"     : len(wins),
        "losses"   : len(losses),
        "win_rate" : len(wins) / len(t) * 100,
        "avg_pnl"  : np.mean([x["pnl_usdt"] for x in t]),
        "total_pnl": sum(x["pnl_usdt"] for x in t),
        "avg_pct"  : np.mean([x["pnl_pct"] for x in t]),
    }

# =============================================================
# PART 1: FULL GRID SEARCH (OS x OB)
# =============================================================
oversold_vals   = list(range(25, 36))   # 25..35
overbought_vals = list(range(65, 76))   # 65..75

results = []
total   = len(oversold_vals) * len(overbought_vals)
orig_print(f"Running {total} kombinasi RSI grid search...\n")

count = 0
for os_val, ob_val in itertools.product(oversold_vals, overbought_vals):
    count += 1
    backtest.RSI_OVERSOLD   = os_val
    backtest.RSI_OVERBOUGHT = ob_val

    builtins.print = dummy_print
    try:
        df_res, trades, *_ = backtest.run_backtest(df_ind)
        builtins.print = orig_print
        if not trades:
            continue
        stats    = backtest.compute_stats(trades, backtest.INITIAL_CAPITAL, df_res["equity"])
        l_stats  = get_side_stats(trades, "LONG")
        s_stats  = get_side_stats(trades, "SHORT")
        results.append({
            "oversold"      : os_val,
            "overbought"    : ob_val,
            "return_pct"    : round(stats["total_return_pct"], 2),
            "final_eq"      : round(stats["final_equity"], 2),
            "max_dd_pct"    : round(stats["max_drawdown_pct"], 2),
            "win_rate"      : round(stats["win_rate"], 1),
            "profit_factor" : round(stats["profit_factor"], 2),
            "calmar"        : round(stats["calmar_ratio"], 2),
            "sharpe"        : round(stats["sharpe_ratio"], 2),
            "trades"        : stats["total_trades"],
            "sl_hits"       : stats["sl_count"],
            "cb_hits"       : stats["cb_count"],
            # Long
            "long_count"    : l_stats["count"],
            "long_wins"     : l_stats["wins"],
            "long_wr"       : round(l_stats["win_rate"], 1),
            "long_avg_pct"  : round(l_stats["avg_pct"], 2),
            "long_total_pnl": round(l_stats["total_pnl"], 2),
            # Short
            "short_count"   : s_stats["count"],
            "short_wins"    : s_stats["wins"],
            "short_wr"      : round(s_stats["win_rate"], 1),
            "short_avg_pct" : round(s_stats["avg_pct"], 2),
            "short_total_pnl": round(s_stats["total_pnl"], 2),
        })
    except Exception as e:
        builtins.print = orig_print

    if count % 20 == 0:
        orig_print(f"  Progress: {count}/{total}...")

orig_print(f"  Selesai: {len(results)} kombinasi valid.\n")

df_all = pd.DataFrame(results).sort_values("return_pct", ascending=False).reset_index(drop=True)

# =============================================================
# CETAK: TOP 25 KOMBINASI (RETURN)
# =============================================================
W = 135
orig_print("="*W)
orig_print("  TOP 25 KOMBINASI RSI — Sorted by Return (Tertinggi → Terendah)")
orig_print("="*W)
header = (f"  {'#':>3} | {'OS':>4} {'OB':>4} | {'Return%':>10} | {'Equity($)':>14} | "
          f"{'Max DD%':>8} | {'Win%':>6} | {'PF':>5} | {'Calmar':>7} | {'Sharpe':>6} | "
          f"{'Trades':>6} | {'SL':>3} | {'CB':>3}")
orig_print(header)
orig_print("-"*W)
for i, row in df_all.head(25).iterrows():
    mark = " ◀ CURRENT" if row["oversold"]==30 and row["overbought"]==70 else ""
    orig_print(
        f"  {i+1:>3} | {int(row['oversold']):>4} {int(row['overbought']):>4} | "
        f"{row['return_pct']:>+10.2f}% | ${row['final_eq']:>13,.0f} | "
        f"{row['max_dd_pct']:>+8.2f}% | {row['win_rate']:>5.1f}% | "
        f"{row['profit_factor']:>5.2f}x | {row['calmar']:>7.2f} | "
        f"{row['sharpe']:>6.2f} | {row['trades']:>6} | "
        f"{int(row['sl_hits']):>3} | {int(row['cb_hits']):>3}{mark}"
    )

# =============================================================
# CETAK: HEATMAP RETURN% (FULL GRID)
# =============================================================
orig_print("\n" + "="*W)
orig_print("  HEATMAP RETURN% — Baris=RSI Oversold (Long Trigger) | Kolom=RSI Overbought (Short Trigger)")
orig_print("="*W)
pivot_ret = df_all.pivot_table(index="oversold", columns="overbought", values="return_pct", aggfunc="first")
pivot_ret = pivot_ret.sort_index(ascending=True)

orig_print(f"  {'OS\\OB':>6}" + "".join(f" | {int(c):>9}" for c in pivot_ret.columns))
orig_print("-"*W)
for os_val, row in pivot_ret.iterrows():
    line = f"  {int(os_val):>6}"
    for val in row.values:
        if pd.isna(val):
            line += " |       N/A"
        else:
            mark = "**" if val == pivot_ret.values[~np.isnan(pivot_ret.values)].max() else "  "
            line += f" |{mark}{val:>+8.0f}%"
    orig_print(line)
orig_print("  ** = Nilai tertinggi\n")

# =============================================================
# CETAK: HEATMAP DRAWDOWN
# =============================================================
orig_print("="*W)
orig_print("  HEATMAP MAX DRAWDOWN % — (Semakin kecil angkanya, semakin aman)")
orig_print("="*W)
pivot_dd = df_all.pivot_table(index="oversold", columns="overbought", values="max_dd_pct", aggfunc="first")
pivot_dd = pivot_dd.sort_index(ascending=True)

orig_print(f"  {'OS\\OB':>6}" + "".join(f" | {int(c):>9}" for c in pivot_dd.columns))
orig_print("-"*W)
for os_val, row in pivot_dd.iterrows():
    line = f"  {int(os_val):>6}"
    for val in row.values:
        if pd.isna(val):
            line += " |       N/A"
        else:
            line += f" |  {val:>+7.1f}%"
    orig_print(line)

# =============================================================
# CETAK: ANALISIS LONG — Best Oversold threshold
# =============================================================
orig_print("\n" + "="*W)
orig_print("  ANALISIS RSI LONG (OVERSOLD) — Baris=tiap nilai OS, rata2 dari semua OB")
orig_print("  Pertanyaan: RSI Oversold berapa yang menghasilkan LONG terbaik?")
orig_print("="*W)

long_summary = []
for os_val in oversold_vals:
    subset = df_all[df_all["oversold"] == os_val]
    if subset.empty:
        continue
    long_summary.append({
        "oversold"        : os_val,
        "avg_return"      : subset["return_pct"].mean(),
        "best_return"     : subset["return_pct"].max(),
        "avg_long_wr"     : subset["long_wr"].mean(),
        "avg_long_pct"    : subset["long_avg_pct"].mean(),
        "avg_long_pnl"    : subset["long_total_pnl"].mean(),
        "avg_long_count"  : subset["long_count"].mean(),
        "avg_long_wins"   : subset["long_wins"].mean(),
    })

ldf = pd.DataFrame(long_summary).sort_values("avg_long_pnl", ascending=False)
orig_print(f"\n  {'Oversold':>8} | {'BestReturn%':>12} | {'LongWin%':>9} | {'AvgPnL%/trade':>14} | "
           f"{'TotalLongPnL($)':>16} | {'Trades':>6} | {'Wins':>5}")
orig_print("-"*100)
for _, row in ldf.iterrows():
    mark = " ◀ CURRENT" if row["oversold"] == 30 else ""
    orig_print(
        f"  {int(row['oversold']):>8} | {row['best_return']:>+12.2f}% | {row['avg_long_wr']:>8.1f}% | "
        f"{row['avg_long_pct']:>+14.2f}% | ${row['avg_long_pnl']:>15,.0f} | "
        f"{row['avg_long_count']:>6.1f} | {row['avg_long_wins']:>5.1f}{mark}"
    )

orig_print(f"\n  Insight Long:")
best_long_os = ldf.iloc[0]["oversold"]
best_long_wr = ldf.iloc[0]["avg_long_wr"]
best_long_pnl = ldf.iloc[0]["avg_long_pnl"]
orig_print(f"  → RSI Oversold TERBAIK untuk LONG : {int(best_long_os)} (Win Rate {best_long_wr:.1f}%, avg PnL ${best_long_pnl:,.0f})")
orig_print(f"  → OS terlalu tinggi (31+)          : Win rate mulai drops, entry terlalu sering = banyak false signals")
orig_print(f"  → OS terlalu rendah (25-27)         : Entry terlalu jarang, kehilangan banyak momentum")

# =============================================================
# CETAK: ANALISIS SHORT — Best Overbought threshold
# =============================================================
orig_print("\n" + "="*W)
orig_print("  ANALISIS RSI SHORT (OVERBOUGHT) — Kolom=tiap nilai OB, rata2 dari semua OS")
orig_print("  Pertanyaan: RSI Overbought berapa yang menghasilkan SHORT terbaik?")
orig_print("="*W)

short_summary = []
for ob_val in overbought_vals:
    subset = df_all[df_all["overbought"] == ob_val]
    if subset.empty:
        continue
    short_summary.append({
        "overbought"       : ob_val,
        "avg_return"       : subset["return_pct"].mean(),
        "best_return"      : subset["return_pct"].max(),
        "avg_short_wr"     : subset["short_wr"].mean(),
        "avg_short_pct"    : subset["short_avg_pct"].mean(),
        "avg_short_pnl"    : subset["short_total_pnl"].mean(),
        "avg_short_count"  : subset["short_count"].mean(),
        "avg_short_wins"   : subset["short_wins"].mean(),
    })

sdf = pd.DataFrame(short_summary).sort_values("avg_short_pnl", ascending=False)
orig_print(f"\n  {'Overbought':>10} | {'BestReturn%':>12} | {'ShortWin%':>10} | {'AvgPnL%/trade':>14} | "
           f"{'TotalShortPnL($)':>17} | {'Trades':>6} | {'Wins':>5}")
orig_print("-"*100)
for _, row in sdf.iterrows():
    mark = " ◀ CURRENT" if row["overbought"] == 70 else ""
    orig_print(
        f"  {int(row['overbought']):>10} | {row['best_return']:>+12.2f}% | {row['avg_short_wr']:>9.1f}% | "
        f"{row['avg_short_pct']:>+14.2f}% | ${row['avg_short_pnl']:>16,.0f} | "
        f"{row['avg_short_count']:>6.1f} | {row['avg_short_wins']:>5.1f}{mark}"
    )

orig_print(f"\n  Insight Short:")
best_short_ob = sdf.iloc[0]["overbought"]
best_short_wr = sdf.iloc[0]["avg_short_wr"]
best_short_pnl = sdf.iloc[0]["avg_short_pnl"]
orig_print(f"  → RSI Overbought TERBAIK untuk SHORT : {int(best_short_ob)} (Win Rate {best_short_wr:.1f}%, avg PnL ${best_short_pnl:,.0f})")
orig_print(f"  → OB terlalu rendah (65-67)           : Short terlalu sering masuk, banyak false shorts")
orig_print(f"  → OB terlalu tinggi (73+)              : Short jarang trigger, sering miss rally lalu crash")

# =============================================================
# CETAK: REKOMENDASI AKHIR
# =============================================================
orig_print("\n" + "="*W)
orig_print("  REKOMENDASI FINAL")
orig_print("="*W)
best_overall     = df_all.iloc[0]
best_risk_adj    = df_all.sort_values("calmar", ascending=False).iloc[0]

orig_print(f"\n  [1] Best Return (Agresif):")
orig_print(f"      RSI Oversold={int(best_overall['oversold'])}, Overbought={int(best_overall['overbought'])}")
orig_print(f"      Return={best_overall['return_pct']:+.2f}% | Equity=${best_overall['final_eq']:,.0f} | DD={best_overall['max_dd_pct']:.2f}% | Calmar={best_overall['calmar']:.2f}")

orig_print(f"\n  [2] Best Risk-Adjusted (Calmar):")
orig_print(f"      RSI Oversold={int(best_risk_adj['oversold'])}, Overbought={int(best_risk_adj['overbought'])}")
orig_print(f"      Return={best_risk_adj['return_pct']:+.2f}% | Equity=${best_risk_adj['final_eq']:,.0f} | DD={best_risk_adj['max_dd_pct']:.2f}% | Calmar={best_risk_adj['calmar']:.2f}")

orig_print(f"\n  [3] Current Config: RSI Oversold=30, Overbought=70")
cur = df_all[(df_all["oversold"]==30) & (df_all["overbought"]==70)]
if not cur.empty:
    c = cur.iloc[0]
    orig_print(f"      Return={c['return_pct']:+.2f}% | Equity=${c['final_eq']:,.0f} | DD={c['max_dd_pct']:.2f}% | Calmar={c['calmar']:.2f}")

orig_print("="*W)

# Reset
backtest.RSI_OVERSOLD   = 30
backtest.RSI_OVERBOUGHT = 70
