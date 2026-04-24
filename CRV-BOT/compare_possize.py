"""
optimize_possize_v2.py - Position Size grid with NEW BB(17,1.8) + RSI(30,71)
Tests: 50% to 100% in 2% steps
"""
import backtest
import builtins

def dummy_print(*args, **kwargs):
    pass
orig_print = builtins.print

orig_print("Fetching data...")
builtins.print = dummy_print
df_raw = backtest.fetch_ohlcv_1y()
builtins.print = orig_print

# Fixed params (all optimal)
backtest.STOP_LOSS_PCT      = 0.20
backtest.CIRCUIT_BREAKER_DD = 0.50
backtest.COOLDOWN_CANDLES   = 6
backtest.LEVERAGE           = 2
backtest.RSI_OVERSOLD       = 30
backtest.RSI_OVERBOUGHT     = 71
backtest.BB_PERIOD          = 17
backtest.BB_STD_DEV         = 1.8

# Recompute indicators with new BB
builtins.print = dummy_print
df_ind = backtest.compute_indicators(df_raw)
builtins.print = orig_print

sizes = [0.50, 0.52, 0.54, 0.56, 0.58, 0.60,
         0.62, 0.64, 0.66, 0.68, 0.70,
         0.72, 0.74, 0.76, 0.78, 0.80,
         0.82, 0.84, 0.86, 0.88, 0.90,
         0.92, 0.94, 0.96, 0.98, 1.00]

results = []
orig_print(f"\nTesting {len(sizes)} position sizes (50%-100%, step 2%)...\n")

for sz in sizes:
    backtest.POSITION_SIZE_PCT = sz
    builtins.print = dummy_print
    df_res, trades, *_ = backtest.run_backtest(df_ind)
    if not trades:
        builtins.print = orig_print
        continue
    stats = backtest.compute_stats(trades, backtest.INITIAL_CAPITAL, df_res["equity"])
    builtins.print = orig_print

    results.append({
        "size"          : sz,
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
    })

# Print table
W = 130
orig_print("="*W)
orig_print("  POSITION SIZE OPTIMIZATION — BB(17,1.8) + RSI(30/71) + SL20% + CB50% + CD24h")
orig_print("="*W)
orig_print(f"  {'#':>3} | {'Size%':>6} | {'Return%':>12} | {'Final Equity':>16} | {'Max DD%':>8} | {'Win%':>6} | {'PF':>5} | {'Calmar':>8} | {'Sharpe':>6} | {'Trades':>6} | {'SL':>3} | {'CB':>3}")
orig_print("-"*W)

for i, r in enumerate(results):
    mark = ""
    if r["size"] == 0.92:
        mark = " ◀ CURRENT"
    elif r["size"] == 1.00:
        mark = " ◀ ALL-IN"
    
    # Find best return
    best_ret = max(results, key=lambda x: x["return_pct"])["return_pct"]
    if r["return_pct"] == best_ret:
        mark = " ⭐ BEST"
    
    orig_print(
        f"  {i+1:>3} | {r['size']*100:>5.0f}% | "
        f"{r['return_pct']:>+12.2f}% | ${r['final_eq']:>15,.0f} | "
        f"{r['max_dd_pct']:>+8.2f}% | {r['win_rate']:>5.1f}% | "
        f"{r['profit_factor']:>5.2f}x | {r['calmar']:>8.2f} | "
        f"{r['sharpe']:>6.2f} | {r['trades']:>6} | "
        f"{r['sl_hits']:>3} | {r['cb_hits']:>3}{mark}"
    )

# Summary
orig_print("\n" + "="*W)
orig_print("  RINGKASAN")
orig_print("="*W)

best_ret   = max(results, key=lambda x: x["return_pct"])
best_cal   = max(results, key=lambda x: x["calmar"])
cur        = next((r for r in results if r["size"] == 0.92), None)
allin      = next((r for r in results if r["size"] == 1.00), None)

orig_print(f"\n  [BEST RETURN]    : Size={best_ret['size']*100:.0f}%")
orig_print(f"                     Return={best_ret['return_pct']:+.2f}% | Equity=${best_ret['final_eq']:,.0f} | DD={best_ret['max_dd_pct']:.2f}% | Calmar={best_ret['calmar']:.2f}")

orig_print(f"\n  [BEST CALMAR]    : Size={best_cal['size']*100:.0f}%")
orig_print(f"                     Return={best_cal['return_pct']:+.2f}% | Equity=${best_cal['final_eq']:,.0f} | DD={best_cal['max_dd_pct']:.2f}% | Calmar={best_cal['calmar']:.2f}")

if cur:
    orig_print(f"\n  [CURRENT 92%]    : Return={cur['return_pct']:+.2f}% | Equity=${cur['final_eq']:,.0f} | DD={cur['max_dd_pct']:.2f}%")

if allin:
    orig_print(f"  [ALL-IN 100%]    : Return={allin['return_pct']:+.2f}% | Equity=${allin['final_eq']:,.0f} | DD={allin['max_dd_pct']:.2f}%")

if best_ret and allin:
    diff = best_ret['final_eq'] - allin['final_eq']
    orig_print(f"\n  Best vs All-in   : +${diff:,.0f} lebih banyak ({best_ret['size']*100:.0f}% vs 100%)")

orig_print("="*W)

# Reset
backtest.POSITION_SIZE_PCT = 0.92
