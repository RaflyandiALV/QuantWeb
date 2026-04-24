"""
Optimize COOLDOWN_CANDLES parameter (SL=20%, CB=50% fixed).
Tests: 0 (no cooldown), 1, 2, 3, 4, 5, 6, 8, 10, 12, 18, 24 candles.
Each 4H candle = 4 hours, so 6 candles = 24 jam jeda.
"""
import backtest
import pandas as pd
import builtins

def dummy_print(*args, **kwargs):
    pass

orig_print = builtins.print

def run_cooldown_optimization():
    orig_print("Fetching data (1 year) for Cooldown optimization...")
    builtins.print = dummy_print
    df_raw = backtest.fetch_ohlcv_1y()
    df_ind = backtest.compute_indicators(df_raw)
    builtins.print = orig_print
    
    cooldown_values = [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 18, 24]
    results = []
    
    # Fix SL and CB at optimal values
    backtest.STOP_LOSS_PCT = 0.20
    backtest.CIRCUIT_BREAKER_DD = 0.50
    
    orig_print("Running Cooldown optimization loop (SL=20%, CB=50% fixed)...")
    orig_print(f"{'CD':<4} | {'Jeda (jam)':<10} | {'Final Eq ($)':<14} | {'Return %':<10} | {'Max DD %':<10} | {'Trades':<8} | {'Win %':<7} | {'SL':<4} | {'CB':<4}")
    orig_print("-" * 95)
    
    for cd in cooldown_values:
        backtest.COOLDOWN_CANDLES = cd
        
        builtins.print = dummy_print 
        df_res, trades, sig_l, sig_s, sig_sl, sig_cb = backtest.run_backtest(df_ind)
        equity_curve = df_res["equity"]
        stats = backtest.compute_stats(trades, backtest.INITIAL_CAPITAL, equity_curve)
        builtins.print = orig_print
        
        final_eq = stats.get('final_equity', backtest.INITIAL_CAPITAL)
        ret_pct = stats.get('total_return_pct', 0)
        max_dd = stats.get('max_drawdown_pct', 0)
        num_trades = stats.get('total_trades', 0)
        win_rate = stats.get('win_rate', 0)
        sl_hits = sum(1 for t in trades if t['exit_reason'] == 'stop_loss')
        cb_hits = sum(1 for t in trades if t['exit_reason'] == 'circuit_breaker')
        jeda_jam = cd * 4  # each candle = 4 hours
        
        results.append({
            'cooldown': cd,
            'jeda_jam': jeda_jam,
            'final_equity': final_eq,
            'total_return': ret_pct,
            'max_drawdown': max_dd,
            'total_trades': num_trades,
            'win_rate': win_rate,
            'sl_hits': sl_hits,
            'cb_hits': cb_hits
        })
        
        orig_print(f"{cd:<4} | {jeda_jam:<10} | {final_eq:<14,.2f} | {ret_pct:>+8.2f}% | {max_dd:>+8.2f}% | {num_trades:<8} | {win_rate:>5.1f}% | {sl_hits:<4} | {cb_hits:<4}")

    # Best by return
    best_ret = max(results, key=lambda x: x['total_return'])
    orig_print("\n==============================================")
    orig_print(">>> BEST PERFORMER BY TOTAL RETURN <<<")
    orig_print("==============================================")
    orig_print(f"Cooldown Candles         : {best_ret['cooldown']} ({best_ret['jeda_jam']} jam)")
    orig_print(f"Final Equity             : ${best_ret['final_equity']:,.2f}")
    orig_print(f"Total Return             : {best_ret['total_return']:+.2f}%")
    orig_print(f"Max Drawdown             : {best_ret['max_drawdown']:+.2f}%")
    orig_print(f"Win Rate                 : {best_ret['win_rate']:.1f}%")
    orig_print(f"SL Hits / CB Hits        : {best_ret['sl_hits']} / {best_ret['cb_hits']}")

    # Best by risk-adjusted (return / abs(max_dd))
    for r in results:
        r['risk_adj'] = r['total_return'] / abs(r['max_drawdown']) if r['max_drawdown'] != 0 else 0
    best_risk = max(results, key=lambda x: x['risk_adj'])
    orig_print("\n==============================================")
    orig_print(">>> BEST RISK-ADJUSTED (Return/MaxDD) <<<")
    orig_print("==============================================")
    orig_print(f"Cooldown Candles         : {best_risk['cooldown']} ({best_risk['jeda_jam']} jam)")
    orig_print(f"Final Equity             : ${best_risk['final_equity']:,.2f}")
    orig_print(f"Total Return             : {best_risk['total_return']:+.2f}%")
    orig_print(f"Max Drawdown             : {best_risk['max_drawdown']:+.2f}%")
    orig_print(f"Risk-Adjusted Score      : {best_risk['risk_adj']:.2f}")
    orig_print(f"Win Rate                 : {best_risk['win_rate']:.1f}%")

if __name__ == "__main__":
    run_cooldown_optimization()
