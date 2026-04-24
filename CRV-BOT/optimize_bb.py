"""
optimize_bb.py - Grid Search Bollinger Bands Parameters
BB Period (15-25) x BB StdDev (1.5-2.5, step 0.1)
"""
import backtest
import builtins
import pandas as pd
import numpy as np
import itertools

def dummy_print(*args, **kwargs):
    pass

orig_print = builtins.print

# --- Fetch data sekali ---
orig_print("Fetching data...")
builtins.print = dummy_print
df_raw = backtest.fetch_ohlcv_1y()
builtins.print = orig_print
orig_print(f"Data OK: {len(df_raw)} candles\n")

# --- Parameter tetap (optimal dari optimasi sebelumnya) ---
backtest.STOP_LOSS_PCT      = 0.20
backtest.CIRCUIT_BREAKER_DD = 0.50
backtest.COOLDOWN_CANDLES   = 6
backtest.POSITION_SIZE_PCT  = 0.92
backtest.LEVERAGE           = 2
backtest.RSI_OVERSOLD       = 30
backtest.RSI_OVERBOUGHT     = 71

# --- Grid BB ---
bb_periods = list(range(15, 26))                              # 15..25
bb_stddevs = [round(x * 0.1, 1) for x in range(15, 26)]      # 1.5..2.5

results = []
total   = len(bb_periods) * len(bb_stddevs)
orig_print(f"Running {total} kombinasi BB (Period x StdDev)...\n")

count = 0
for period, stddev in itertools.product(bb_periods, bb_stddevs):
    count += 1
    backtest.BB_PERIOD  = period
    backtest.BB_STD_DEV = stddev

    builtins.print = dummy_print
    try:
        # Harus recompute indicators karena BB_PERIOD berubah
        df_ind = backtest.compute_indicators(df_raw)
        df_res, trades, *_ = backtest.run_backtest(df_ind)
        builtins.print = orig_print
        if not trades:
            continue
        stats = backtest.compute_stats(trades, backtest.INITIAL_CAPITAL, df_res["equity"])

        # Per-side
        longs  = [t for t in trades if t["direction"] == "LONG"]
        shorts = [t for t in trades if t["direction"] == "SHORT"]
        l_wr = (len([t for t in longs if t["pnl_usdt"]>0]) / len(longs) * 100) if longs else 0
        s_wr = (len([t for t in shorts if t["pnl_usdt"]>0]) / len(shorts) * 100) if shorts else 0

        results.append({
            "period"        : period,
            "stddev"        : stddev,
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
            "long_count"    : len(longs),
            "short_count"   : len(shorts),
            "long_wr"       : round(l_wr, 1),
            "short_wr"      : round(s_wr, 1),
        })
    except Exception as e:
        builtins.print = orig_print

    if count % 20 == 0:
        orig_print(f"  Progress: {count}/{total}...")

orig_print(f"  Selesai: {len(results)} kombinasi valid.\n")

df_all = pd.DataFrame(results).sort_values("return_pct", ascending=False).reset_index(drop=True)

W = 140

# =============================================================
# TOP 25 by Return
# =============================================================
orig_print("="*W)
orig_print("  TOP 25 KOMBINASI BB — Sorted by Return")
orig_print("="*W)
orig_print(f"  {'#':>3} | {'Period':>6} {'StdDev':>7} | {'Return%':>10} | {'Equity($)':>14} | "
           f"{'Max DD%':>8} | {'Win%':>6} | {'PF':>5} | {'Calmar':>7} | {'Sharpe':>6} | "
           f"{'Trades':>6} | {'L/S':>6} | {'LWR%':>5} {'SWR%':>5} | {'SL':>3} {'CB':>3}")
orig_print("-"*W)
for i, row in df_all.head(25).iterrows():
    mark = " ◀ CURRENT" if row["period"]==20 and row["stddev"]==2.0 else ""
    orig_print(
        f"  {i+1:>3} | {int(row['period']):>6} {row['stddev']:>7.1f} | "
        f"{row['return_pct']:>+10.2f}% | ${row['final_eq']:>13,.0f} | "
        f"{row['max_dd_pct']:>+8.2f}% | {row['win_rate']:>5.1f}% | "
        f"{row['profit_factor']:>5.2f}x | {row['calmar']:>7.2f} | "
        f"{row['sharpe']:>6.2f} | {row['trades']:>6} | "
        f"{int(row['long_count']):>3}/{int(row['short_count']):<3}| "
        f"{row['long_wr']:>5.1f} {row['short_wr']:>5.1f} | "
        f"{int(row['sl_hits']):>3} {int(row['cb_hits']):>3}{mark}"
    )

# =============================================================
# TOP 10 by Calmar
# =============================================================
df_calmar = df_all.sort_values("calmar", ascending=False).head(10)
orig_print("\n" + "="*W)
orig_print("  TOP 10 by CALMAR (Best Risk-Adjusted)")
orig_print("="*W)
orig_print(f"  {'#':>3} | {'Period':>6} {'StdDev':>7} | {'Return%':>10} | {'MaxDD%':>8} | {'Calmar':>7} | {'PF':>5} | {'Trades':>6}")
orig_print("-"*80)
for i, (_, row) in enumerate(df_calmar.iterrows()):
    mark = " ◀ CURRENT" if row["period"]==20 and row["stddev"]==2.0 else ""
    orig_print(
        f"  {i+1:>3} | {int(row['period']):>6} {row['stddev']:>7.1f} | "
        f"{row['return_pct']:>+10.2f}% | {row['max_dd_pct']:>+8.2f}% | "
        f"{row['calmar']:>7.2f} | {row['profit_factor']:>5.2f}x | {row['trades']:>6}{mark}"
    )

# =============================================================
# HEATMAP RETURN% (Period x StdDev)
# =============================================================
orig_print("\n" + "="*W)
orig_print("  HEATMAP RETURN% — Baris=BB Period | Kolom=BB StdDev")
orig_print("="*W)
pivot_ret = df_all.pivot_table(index="period", columns="stddev", values="return_pct", aggfunc="first")
pivot_ret = pivot_ret.sort_index(ascending=True)

orig_print(f"  {'P\\SD':>6}" + "".join(f" | {c:>9.1f}" for c in pivot_ret.columns))
orig_print("-"*W)
for p, row in pivot_ret.iterrows():
    line = f"  {int(p):>6}"
    best_val = pivot_ret.values[~np.isnan(pivot_ret.values)].max() if len(pivot_ret.values[~np.isnan(pivot_ret.values)]) > 0 else 0
    for val in row.values:
        if pd.isna(val):
            line += " |       N/A"
        else:
            mark = "**" if val == best_val else "  "
            line += f" |{mark}{val:>+8.0f}%"
    orig_print(line)
orig_print("  ** = Nilai tertinggi")

# =============================================================
# HEATMAP MAX DRAWDOWN
# =============================================================
orig_print("\n" + "="*W)
orig_print("  HEATMAP MAX DRAWDOWN% — (Semakin mendekati 0, semakin aman)")
orig_print("="*W)
pivot_dd = df_all.pivot_table(index="period", columns="stddev", values="max_dd_pct", aggfunc="first")
pivot_dd = pivot_dd.sort_index(ascending=True)

orig_print(f"  {'P\\SD':>6}" + "".join(f" | {c:>9.1f}" for c in pivot_dd.columns))
orig_print("-"*W)
for p, row in pivot_dd.iterrows():
    line = f"  {int(p):>6}"
    for val in row.values:
        if pd.isna(val):
            line += " |       N/A"
        else:
            line += f" |  {val:>+7.1f}%"
    orig_print(line)

# =============================================================
# HEATMAP CALMAR RATIO
# =============================================================
orig_print("\n" + "="*W)
orig_print("  HEATMAP CALMAR RATIO — (Semakin tinggi, semakin baik risk-adjusted)")
orig_print("="*W)
pivot_cal = df_all.pivot_table(index="period", columns="stddev", values="calmar", aggfunc="first")
pivot_cal = pivot_cal.sort_index(ascending=True)

orig_print(f"  {'P\\SD':>6}" + "".join(f" | {c:>9.1f}" for c in pivot_cal.columns))
orig_print("-"*W)
for p, row in pivot_cal.iterrows():
    line = f"  {int(p):>6}"
    for val in row.values:
        if pd.isna(val):
            line += " |       N/A"
        else:
            line += f" |  {val:>8.1f}"
    orig_print(line)

# =============================================================
# ANALISIS PER PERIOD (rata2 dari semua StdDev)
# =============================================================
orig_print("\n" + "="*W)
orig_print("  ANALISIS PER BB PERIOD (rata-rata dari semua StdDev)")
orig_print("="*W)
period_summary = []
for p in bb_periods:
    subset = df_all[df_all["period"] == p]
    if subset.empty:
        continue
    period_summary.append({
        "period"       : p,
        "avg_return"   : subset["return_pct"].mean(),
        "best_return"  : subset["return_pct"].max(),
        "avg_dd"       : subset["max_dd_pct"].mean(),
        "avg_calmar"   : subset["calmar"].mean(),
        "avg_trades"   : subset["trades"].mean(),
        "avg_wr"       : subset["win_rate"].mean(),
    })

pdf = pd.DataFrame(period_summary).sort_values("avg_return", ascending=False)
orig_print(f"  {'Period':>6} | {'AvgReturn%':>11} | {'BestReturn%':>12} | {'AvgDD%':>8} | {'AvgCalmar':>10} | {'AvgTrades':>9} | {'AvgWR%':>7}")
orig_print("-"*80)
for _, row in pdf.iterrows():
    mark = " ◀ CURRENT" if row["period"] == 20 else ""
    orig_print(
        f"  {int(row['period']):>6} | {row['avg_return']:>+11.2f}% | {row['best_return']:>+12.2f}% | "
        f"{row['avg_dd']:>+8.2f}% | {row['avg_calmar']:>10.2f} | "
        f"{row['avg_trades']:>9.1f} | {row['avg_wr']:>6.1f}%{mark}"
    )

# =============================================================
# ANALISIS PER STDDEV (rata2 dari semua Period)
# =============================================================
orig_print("\n" + "="*W)
orig_print("  ANALISIS PER BB STDDEV (rata-rata dari semua Period)")
orig_print("="*W)
sd_summary = []
for sd in bb_stddevs:
    subset = df_all[df_all["stddev"] == sd]
    if subset.empty:
        continue
    sd_summary.append({
        "stddev"       : sd,
        "avg_return"   : subset["return_pct"].mean(),
        "best_return"  : subset["return_pct"].max(),
        "avg_dd"       : subset["max_dd_pct"].mean(),
        "avg_calmar"   : subset["calmar"].mean(),
        "avg_trades"   : subset["trades"].mean(),
        "avg_wr"       : subset["win_rate"].mean(),
    })

sdf = pd.DataFrame(sd_summary).sort_values("avg_return", ascending=False)
orig_print(f"  {'StdDev':>7} | {'AvgReturn%':>11} | {'BestReturn%':>12} | {'AvgDD%':>8} | {'AvgCalmar':>10} | {'AvgTrades':>9} | {'AvgWR%':>7}")
orig_print("-"*80)
for _, row in sdf.iterrows():
    mark = " ◀ CURRENT" if row["stddev"] == 2.0 else ""
    orig_print(
        f"  {row['stddev']:>7.1f} | {row['avg_return']:>+11.2f}% | {row['best_return']:>+12.2f}% | "
        f"{row['avg_dd']:>+8.2f}% | {row['avg_calmar']:>10.2f} | "
        f"{row['avg_trades']:>9.1f} | {row['avg_wr']:>6.1f}%{mark}"
    )

# =============================================================
# REKOMENDASI FINAL
# =============================================================
best_ret   = df_all.iloc[0]
best_cal   = df_all.sort_values("calmar", ascending=False).iloc[0]
cur        = df_all[(df_all["period"]==20) & (df_all["stddev"]==2.0)]

orig_print("\n" + "="*W)
orig_print("  REKOMENDASI FINAL")
orig_print("="*W)
orig_print(f"\n  [1] Best Return:")
orig_print(f"      BB Period={int(best_ret['period'])}, StdDev={best_ret['stddev']:.1f}")
orig_print(f"      Return={best_ret['return_pct']:+.2f}% | Equity=${best_ret['final_eq']:,.0f} | DD={best_ret['max_dd_pct']:.2f}% | Calmar={best_ret['calmar']:.2f}")

orig_print(f"\n  [2] Best Calmar (Risk-Adjusted):")
orig_print(f"      BB Period={int(best_cal['period'])}, StdDev={best_cal['stddev']:.1f}")
orig_print(f"      Return={best_cal['return_pct']:+.2f}% | Equity=${best_cal['final_eq']:,.0f} | DD={best_cal['max_dd_pct']:.2f}% | Calmar={best_cal['calmar']:.2f}")

if not cur.empty:
    c = cur.iloc[0]
    orig_print(f"\n  [3] Current Config: BB Period=20, StdDev=2.0")
    orig_print(f"      Return={c['return_pct']:+.2f}% | Equity=${c['final_eq']:,.0f} | DD={c['max_dd_pct']:.2f}% | Calmar={c['calmar']:.2f}")

orig_print("="*W)

# Reset
backtest.BB_PERIOD  = 20
backtest.BB_STD_DEV = 2.0
